"""
DataUpdateCoordinator – holt regelmäßig den Stundenplan ab und cached ihn,
sodass mehrere Entities (Sensor, Calendar) sich denselben Datensatz teilen.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import WebUntisAuthError, WebUntisQRClient, parse_period_datetime
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class WebUntisCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """
    Holt einmal pro Polling-Intervall den Stundenplan für heute + 7 Tage
    und stellt das masterData-Mapping (Fächer/Räume/Lehrer-IDs → Namen) bereit.
    """

    def __init__(self, hass: HomeAssistant, client: WebUntisQRClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{client.credentials.user}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        # Wird im ersten Refresh gefüllt – kompletter User+MasterData-Block
        self._user_data: dict[str, Any] | None = None

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
                end=today + timedelta(days=7),
            )

            return {
                "user_data": self._user_data,
                "periods": _enrich_periods(periods, self._user_data),
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
    Reichert Period-Einträge mit lesbaren Namen an.

    WebUntis liefert in den Periods nur IDs für Fach/Raum/Lehrer; die
    Klartextnamen stehen im `masterData`-Block. Wir mappen einmal und
    hängen die fertigen Strings an jede Period.
    """
    master = user_data.get("masterData", {})
    subjects = {s["id"]: s for s in master.get("subjects", [])}
    rooms = {r["id"]: r for r in master.get("rooms", [])}
    teachers = {t["id"]: t for t in master.get("teachers", [])}

    enriched: list[dict[str, Any]] = []
    for p in periods:
        start_dt = parse_period_datetime(p["startDateTime"] // 10000, p["startDateTime"] % 10000) \
            if "startDateTime" in p and isinstance(p["startDateTime"], int) and p["startDateTime"] > 10**8 \
            else _legacy_period_datetime(p, "start")
        end_dt = _legacy_period_datetime(p, "end") if not (
            "endDateTime" in p and isinstance(p["endDateTime"], int) and p["endDateTime"] > 10**8
        ) else parse_period_datetime(p["endDateTime"] // 10000, p["endDateTime"] % 10000)

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
                # Status z.B. REGULAR, CANCELLED, IRREGULAR
                "is_cancelled": p.get("is", {}).get("cancelled", False)
                if isinstance(p.get("is"), dict)
                else "CANCELLED" in (p.get("can", []) or []),
                "raw": p,
            }
        )

    enriched.sort(key=lambda x: x["start"])
    return enriched


def _legacy_period_datetime(period: dict[str, Any], which: str) -> datetime:
    """
    Fallback für ältere WebUntis-Server, die Datum und Zeit getrennt liefern:
    `date` als YYYYMMDD und `startTime`/`endTime` als HHMM.
    """
    d = period.get("date") or period.get(f"{which}Date")
    t = period.get(f"{which}Time")
    if d is None or t is None:
        # Notnagel: jetzt
        return datetime.now()
    return parse_period_datetime(d, t)
