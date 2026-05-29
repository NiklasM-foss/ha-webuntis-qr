"""
Calendar-Plattform: macht den Stundenplan als HA-Kalender verfügbar.

Damit lassen sich Lovelace-Calendar-Cards, Automationen
("wenn nächster Termin … startet") und Sprachausgaben bauen.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WebUntisCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WebUntisCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WebUntisCalendar(coordinator, entry)])


class WebUntisCalendar(CoordinatorEntity[WebUntisCoordinator], CalendarEntity):
    """Ein Kalender pro Konto – enthält alle Periods der nächsten 7 Tage."""

    _attr_has_entity_name = True
    _attr_translation_key = "timetable"

    def __init__(self, coordinator: WebUntisCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_name = "Stundenplan"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "WebUntis",
            "model": "QR-Login",
        }

    def _periods(self) -> list[dict[str, Any]]:
        return (self.coordinator.data or {}).get("periods", []) or []

    @property
    def event(self) -> CalendarEvent | None:
        """Nächstes anstehendes Event – wird in der HA-UI hervorgehoben."""
        # Periods sind timezone-aware (HA-Lokalzeit); now() ebenfalls aware
        now = datetime.now(timezone.utc)
        upcoming = next(
            (p for p in self._periods() if p["end"] > now and not p["is_cancelled"]),
            None,
        )
        if not upcoming:
            return None
        return _to_event(upcoming)

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Liefert alle Periods im gefragten Zeitfenster."""
        # Periods und HA-Range sind beide aware – direkter Vergleich
        return [
            _to_event(p)
            for p in self._periods()
            if p["end"] >= start_date and p["start"] <= end_date
        ]


def _to_event(period: dict[str, Any]) -> CalendarEvent:
    """
    Mappt eine angereicherte Period auf ein CalendarEvent.

    Summary-Format: „<Fach> • <Raum>" – Raum direkt sichtbar im Kalender-Titel,
    nicht nur im optionalen `location`-Feld (das viele HA-Calendar-Cards
    nicht anzeigen).
    """
    subject = period["subject"] or period["subject_long"] or "Stunde"
    room = period["room"]
    summary = f"{subject} • {room}" if room else subject
    if period["is_cancelled"]:
        summary = f"[entfällt] {summary}"

    description_parts = []
    if period["teacher"]:
        description_parts.append(f"Lehrer: {period['teacher']}")
    if period["subject_long"] and period["subject_long"] != period["subject"]:
        description_parts.append(f"Fach: {period['subject_long']}")
    if room:
        description_parts.append(f"Raum: {room}")

    return CalendarEvent(
        start=period["start"],
        end=period["end"],
        summary=summary,
        location=room or None,
        description="\n".join(description_parts) or None,
    )
