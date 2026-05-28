"""
Sensor-Plattform: liefert „nächste Stunde", „aktuelle Stunde" und
„Stunden heute" als Entities.

Jeder Sensor ist eine dünne Sicht auf die im Coordinator gecachten Periods.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity
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
    """Erzeugt die drei Sensor-Entities für diesen ConfigEntry."""
    coordinator: WebUntisCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            NextLessonSensor(coordinator, entry),
            CurrentLessonSensor(coordinator, entry),
            LessonsTodaySensor(coordinator, entry),
        ]
    )


class _Base(CoordinatorEntity[WebUntisCoordinator], SensorEntity):
    """Gemeinsame Basis: identische Device-Info + unique-ID-Schema."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: WebUntisCoordinator, entry: ConfigEntry, key: str
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "WebUntis",
            "model": "QR-Login",
        }

    def _periods(self) -> list[dict[str, Any]]:
        return (self.coordinator.data or {}).get("periods", []) or []


class NextLessonSensor(_Base):
    """Zeigt die nächste anstehende (nicht ausgefallene) Stunde."""

    _attr_translation_key = "next_lesson"
    _attr_icon = "mdi:school"

    def __init__(self, coordinator: WebUntisCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "next_lesson")
        self._attr_name = "Nächste Stunde"

    @property
    def native_value(self) -> str | None:
        # Periods sind timezone-aware (UTC); now() entsprechend aware
        now = datetime.now(timezone.utc)
        # Erste Period, die in der Zukunft liegt und nicht ausgefallen ist
        upcoming = next(
            (p for p in self._periods() if p["end"] > now and not p["is_cancelled"]),
            None,
        )
        if not upcoming:
            return None
        return upcoming["subject"] or upcoming["subject_long"] or "?"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        # Periods sind timezone-aware (UTC); now() entsprechend aware
        now = datetime.now(timezone.utc)
        upcoming = next(
            (p for p in self._periods() if p["end"] > now and not p["is_cancelled"]),
            None,
        )
        if not upcoming:
            return None
        return {
            "start": upcoming["start"].isoformat(),
            "end": upcoming["end"].isoformat(),
            "room": upcoming["room"],
            "teacher": upcoming["teacher"],
            "subject_long": upcoming["subject_long"],
        }


class CurrentLessonSensor(_Base):
    """Stunde, die JETZT gerade läuft – sonst 'frei'."""

    _attr_translation_key = "current_lesson"
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: WebUntisCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "current_lesson")
        self._attr_name = "Aktuelle Stunde"

    @property
    def native_value(self) -> str:
        # Periods sind timezone-aware (UTC); now() entsprechend aware
        now = datetime.now(timezone.utc)
        current = next(
            (p for p in self._periods() if p["start"] <= now < p["end"]),
            None,
        )
        if not current:
            return "frei"
        if current["is_cancelled"]:
            return f"{current['subject']} (entfällt)"
        return current["subject"] or "?"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        # Periods sind timezone-aware (UTC); now() entsprechend aware
        now = datetime.now(timezone.utc)
        current = next(
            (p for p in self._periods() if p["start"] <= now < p["end"]),
            None,
        )
        if not current:
            return None
        return {
            "room": current["room"],
            "teacher": current["teacher"],
            "end": current["end"].isoformat(),
            "cancelled": current["is_cancelled"],
        }


class LessonsTodaySensor(_Base):
    """Anzahl der heutigen Stunden (Ausfälle exklusive)."""

    _attr_translation_key = "lessons_today"
    _attr_icon = "mdi:calendar-today"
    _attr_native_unit_of_measurement = "Stunden"

    def __init__(self, coordinator: WebUntisCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "lessons_today")
        self._attr_name = "Stunden heute"

    @property
    def native_value(self) -> int:
        # date() in lokaler Zeit – Periods sind UTC, also vorher konvertieren
        today = datetime.now().astimezone().date()
        return sum(
            1
            for p in self._periods()
            if p["start"].astimezone().date() == today and not p["is_cancelled"]
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        # date() in lokaler Zeit – Periods sind UTC, also vorher konvertieren
        today = datetime.now().astimezone().date()
        todays = [p for p in self._periods() if p["start"].astimezone().date() == today]
        if not todays:
            return None
        return {
            "first_start": todays[0]["start"].isoformat(),
            "last_end": todays[-1]["end"].isoformat(),
            "cancelled_count": sum(1 for p in todays if p["is_cancelled"]),
            "subjects": [p["subject"] for p in todays],
        }
