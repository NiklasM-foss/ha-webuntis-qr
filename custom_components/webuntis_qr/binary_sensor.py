"""
Binary-Sensor-Plattform.

Bietet derzeit nur einen Sensor: „Änderungen seit letzter Aktualisierung".
Wird true, sobald sich der Stundenplan-Fingerprint zwischen zwei
Coordinator-Refreshes ändert (Ausfall, Vertretung, Raumwechsel, neue Stunde).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    async_add_entities([ChangedSinceLastSensor(coordinator, entry)])


class ChangedSinceLastSensor(
    CoordinatorEntity[WebUntisCoordinator], BinarySensorEntity
):
    """
    True für genau den Refresh-Zyklus, in dem eine Änderung erkannt wurde
    – beim nächsten Poll-Intervall ohne weitere Änderungen kippt der Wert
    automatisch zurück auf False. Ideal als Trigger für Notify-Automationen.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:bell-alert"

    def __init__(
        self, coordinator: WebUntisCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_changed_since_last"
        self._attr_name = "Änderungen seit letzter Aktualisierung"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "WebUntis",
            "model": "QR-Login",
        }

    @property
    def is_on(self) -> bool:
        """True wenn der letzte Refresh inhaltliche Änderungen brachte."""
        return bool((self.coordinator.data or {}).get("changed_since_last", False))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Fingerprint als Attribut – für Debug / Vergleich von außen."""
        data = self.coordinator.data or {}
        return {
            "fingerprint": data.get("fingerprint"),
            "last_update": self.coordinator.last_update_success_time.isoformat()
            if self.coordinator.last_update_success_time
            else None,
        }
