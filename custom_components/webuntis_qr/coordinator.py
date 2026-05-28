"""
DataUpdateCoordinator – holt regelmäßig den Stundenplan ab und cached ihn,
sodass mehrere Entities (Sensor, Calendar) sich denselben Datensatz teilen.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import WebUntisAuthError, WebUntisQRClient
from .const import (
    CONF_LOOKAHEAD_DAYS,
    CONF_SCAN_INTERVAL,
    DEFAULT_LOOKAHEAD_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class WebUntisCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """
    Holt einmal pro Polling-Intervall den Stundenplan für heute + 7 Tage
    und stellt das masterData-Mapping (Fächer/Räume/Lehrer-IDs → Namen) bereit.
    """

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: WebUntisQRClient
    ) -> None:
        # Optionen aus dem Options-Flow lesen (Fallback auf Defaults)
        scan = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{client.credentials.user}",
            update_interval=timedelta(seconds=scan),
        )
        self.client = client
        self._entry = entry
        # Wird im ersten Refresh gefüllt – kompletter User+MasterData-Block
        self._user_data: dict[str, Any] | None = None
        # Fingerprint des letzten Stundenplan-Snapshots – für „Änderungen
        # seit letzter Aktualisierung"-Binary-Sensor
        self._last_fingerprint: str | None = None

    @property
    def lookahead_days(self) -> int:
        """Wie viele Tage Stundenplan ab heute geladen werden."""
        return int(
            self._entry.options.get(CONF_LOOKAHEAD_DAYS, DEFAULT_LOOKAHEAD_DAYS)
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Wird vom Coordinator periodisch aufgerufen."""
        try:
            # Beim allerersten Mal (oder nach Re-Auth): userData holen
            if self._user_data is None:
                self._user_data = await self.client.async_get_user_data()

            # Die Mobile-API gibt das ID-Element als `elemId`/`elemType` zurück,
            # nicht als `personId` (das war die alte Public-API).
            user = self._user_data.get("userData", {})
            elem_id = user.get("elemId") or user.get("personId")
            elem_type = user.get("elemType") or "STUDENT"
            if not elem_id:
                raise UpdateFailed("Keine elemId in userData – Login kaputt?")

            today = date.today()
            periods = await self.client.async_get_timetable(
                elem_id=elem_id,
                elem_type=elem_type,
                start=today,
                end=today + timedelta(days=self.lookahead_days),
            )

            enriched = _enrich_periods(periods, self._user_data)

            # Fingerprint berechnen und mit dem letzten vergleichen, um zu
            # erkennen ob sich der Stundenplan zwischen zwei Refreshes
            # geändert hat (Ausfall, Vertretung, neue Stunde …).
            fingerprint = _periods_fingerprint(enriched)
            changed = (
                self._last_fingerprint is not None
                and fingerprint != self._last_fingerprint
            )
            self._last_fingerprint = fingerprint

            return {
                "user_data": self._user_data,
                "periods": enriched,
                "changed_since_last": changed,
                "fingerprint": fingerprint,
            }
        except WebUntisAuthError as err:
            # Cached userData wegwerfen, damit nächster Versuch neu authentifiziert
            self._user_data = None
            raise UpdateFailed(f"Auth-Fehler: {err}") from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"WebUntis-Abruf fehlgeschlagen: {err}") from err


def _enrich_periods(
    periods: list[dict[str, Any]], user_data: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Reichert Period-Einträge mit lesbaren Namen + geparsten Datumsangaben an.

    Untis Mobile-API-Format (verifiziert gegen bk-luebbecke 2026-05):
      - startDateTime / endDateTime: ISO-Strings, z.B. "2026-05-28T11:10Z"
      - elements:  Liste mit type ∈ {CLASS,TEACHER,SUBJECT,ROOM}
      - is:        Liste von Status-Tags, z.B. ["REGULAR"] oder ["CANCELLED"]
    """
    master = user_data.get("masterData", {})
    subjects = {s["id"]: s for s in master.get("subjects", [])}
    rooms = {r["id"]: r for r in master.get("rooms", [])}
    teachers = {t["id"]: t for t in master.get("teachers", [])}

    enriched: list[dict[str, Any]] = []
    for p in periods:
        try:
            start_dt = _parse_iso(p.get("startDateTime"))
            end_dt = _parse_iso(p.get("endDateTime"))
        except (TypeError, ValueError):
            # Period mit kaputtem Zeitstempel überspringen statt Crash
            continue

        # Status: "CANCELLED" steht direkt in der `is`-Liste
        status = p.get("is", []) or []
        is_cancelled = "CANCELLED" in status

        subject_ids = [e["id"] for e in p.get("elements", []) if e.get("type") == "SUBJECT"]
        room_ids = [e["id"] for e in p.get("elements", []) if e.get("type") == "ROOM"]
        teacher_ids = [e["id"] for e in p.get("elements", []) if e.get("type") == "TEACHER"]

        enriched.append(
            {
                "start": start_dt,
                "end": end_dt,
                "subject": ", ".join(
                    subjects[i]["name"] for i in subject_ids if i in subjects
                ),
                "subject_long": ", ".join(
                    subjects[i].get("longName", subjects[i]["name"])
                    for i in subject_ids
                    if i in subjects
                ),
                "room": ", ".join(rooms[i]["name"] for i in room_ids if i in rooms),
                "teacher": ", ".join(
                    teachers[i]["name"] for i in teacher_ids if i in teachers
                ),
                "is_cancelled": is_cancelled,
                "status": status,
            }
        )

    enriched.sort(key=lambda x: x["start"])
    return enriched


def _periods_fingerprint(periods: list[dict[str, Any]]) -> str:
    """
    Erzeugt einen stabilen Hash über die relevanten Felder aller Periods.

    Wird genutzt, um „echte" Stundenplan-Änderungen (Ausfall, Vertretung,
    Raumwechsel, …) gegen bloße Re-Fetches ohne inhaltliche Änderung zu
    unterscheiden.
    """
    # Periods sind bereits zeitlich sortiert; nur identifizierende Felder
    # in den Hash aufnehmen, damit Anzeige-Reihenfolge nichts kaputt macht.
    compact = [
        {
            "s": p["start"].isoformat(),
            "e": p["end"].isoformat(),
            "su": p.get("subject", ""),
            "r": p.get("room", ""),
            "t": p.get("teacher", ""),
            "c": bool(p.get("is_cancelled")),
        }
        for p in periods
    ]
    blob = json.dumps(compact, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _parse_iso(value: str) -> datetime:
    """
    Parst die ISO-Zeitstempel der Untis-Mobile-API.

    Format ist „2026-05-28T11:10Z" (Sekunden weggelassen, Z für UTC).
    Wir liefern eine timezone-aware UTC-Datetime; HA konvertiert das in
    die Hass-eigene Zeitzone, wenn nötig.
    """
    if not value:
        raise ValueError("leerer Zeitstempel")
    # Sekunden ergänzen falls fehlend; Z → +00:00 für fromisoformat
    v = value.replace("Z", "+00:00")
    # „T11:10+00:00" hat keine Sekunden – das versteht fromisoformat ab 3.11
    try:
        return datetime.fromisoformat(v)
    except ValueError:
        # Notnagel: Sekunden einfügen
        if "T" in v and v.count(":") == 2 + (1 if "+" in v else 0):
            # bereits HH:MM:SS – kein Eingriff nötig
            raise
        # erwartet: YYYY-MM-DDTHH:MM[+/-...]
        date_part, _, tail = v.partition("T")
        time_part, _, tz_part = tail.partition("+") if "+" in tail else tail.partition("-")
        sign = "+" if "+" in tail else "-"
        return datetime.fromisoformat(f"{date_part}T{time_part}:00{sign}{tz_part}")
