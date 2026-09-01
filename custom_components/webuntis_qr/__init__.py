"""
Setup-Einstiegspunkt der WebUntis-QR-Integration.

Wird von Home Assistant aufgerufen, sobald ein ConfigEntry geladen wird.
Hier bauen wir den API-Client + Coordinator und reichen sie an die
Plattform-Module (sensor, binary_sensor, calendar) weiter.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WebUntisCredentials, WebUntisQRClient
from .const import (
    CONF_KEY,
    CONF_SCHOOL,
    CONF_SCHOOL_NUMBER,
    CONF_SERVER,
    CONF_USER,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import WebUntisCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Wird beim Hinzufügen / HA-Start je ConfigEntry aufgerufen."""
    creds = WebUntisCredentials(
        server=entry.data[CONF_SERVER],
        school=entry.data[CONF_SCHOOL],
        user=entry.data[CONF_USER],
        key=entry.data[CONF_KEY],
        school_number=entry.data.get(CONF_SCHOOL_NUMBER),
    )

    session = async_get_clientsession(hass)
    client = WebUntisQRClient(creds, session)
    coordinator = WebUntisCoordinator(hass, entry, client)

    # Erstes Laden synchron abwarten – schlägt das fehl, scheitert das Setup
    await coordinator.async_config_entry_first_refresh()

    # Coordinator unter der Entry-ID ablegen, damit Sensor/Calendar drankommen
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Reload, wenn der User die Options ändert (Intervall / Lookahead)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Plattformen registrieren
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload der Integration, sobald Options geändert wurden."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Räumt beim Entfernen / Reload sauber auf."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
