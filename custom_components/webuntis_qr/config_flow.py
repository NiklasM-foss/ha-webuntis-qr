"""
Config-Flow der WebUntis-QR-Integration.

Der User klebt den vom QR-Code dekodierten Text (untis://setschool?...) ein.
Wir parsen die URI, testen sofort eine Authentifizierung gegen WebUntis
und legen erst dann den ConfigEntry an.

Alternative Eingabe: einzelne Felder (server/school/user/key) – falls der
QR-Reader-Workflow gerade nicht funktioniert oder die Schule die Felder
manuell rausgegeben hat.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    WebUntisAuthError,
    WebUntisCredentials,
    WebUntisQRClient,
    parse_qr_payload,
)
from .const import (
    CONF_KEY,
    CONF_LOOKAHEAD_DAYS,
    CONF_SCAN_INTERVAL,
    CONF_SCHOOL,
    CONF_SCHOOL_NUMBER,
    CONF_SERVER,
    CONF_USER,
    DEFAULT_LOOKAHEAD_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_LOOKAHEAD_DAYS,
    MAX_SCAN_INTERVAL,
    MIN_LOOKAHEAD_DAYS,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# Schema für den "QR-Text einkleben"-Schritt
STEP_QR_SCHEMA = vol.Schema({vol.Required("qr_payload"): str})

# Schema für den manuellen Fallback (Felder einzeln eintippen)
STEP_MANUAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERVER): str,
        vol.Required(CONF_SCHOOL): str,
        vol.Required(CONF_USER): str,
        vol.Required(CONF_KEY): str,
        vol.Optional(CONF_SCHOOL_NUMBER): str,
    }
)


class WebUntisQRConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Erstellt einen neuen ConfigEntry für ein WebUntis-Konto."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "WebUntisOptionsFlow":
        """Hooks HA an, damit der „Konfigurieren"-Button im UI erscheint."""
        return WebUntisOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Erster Schritt: Auswahl zwischen QR-Text und manueller Eingabe."""
        # HA-Menü mit zwei Optionen
        return self.async_show_menu(
            step_id="user",
            menu_options=["qr", "manual"],
        )

    async def async_step_qr(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """User klebt den dekodierten QR-Text ein."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Schritt 1: URI parsen
                creds = parse_qr_payload(user_input["qr_payload"])
            except ValueError as err:
                _LOGGER.warning("QR-Parsing fehlgeschlagen: %s", err)
                errors["base"] = "invalid_qr"
            else:
                # Schritt 2: Login validieren
                result = await self._validate_and_create(creds)
                if result is not None:
                    return result
                errors["base"] = "auth_failed"

        return self.async_show_form(
            step_id="qr",
            data_schema=STEP_QR_SCHEMA,
            errors=errors,
            description_placeholders={
                "example": "untis://setschool?url=ajax.webuntis.com&school=...&user=...&key=..."
            },
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Fallback: einzelne Felder eingeben."""
        errors: dict[str, str] = {}

        if user_input is not None:
            creds = WebUntisCredentials(
                server=user_input[CONF_SERVER].replace("https://", "").rstrip("/"),
                school=user_input[CONF_SCHOOL],
                user=user_input[CONF_USER],
                key=user_input[CONF_KEY].replace(" ", "").upper(),
                school_number=user_input.get(CONF_SCHOOL_NUMBER),
            )
            result = await self._validate_and_create(creds)
            if result is not None:
                return result
            errors["base"] = "auth_failed"

        return self.async_show_form(
            step_id="manual",
            data_schema=STEP_MANUAL_SCHEMA,
            errors=errors,
        )

    async def _validate_and_create(
        self, creds: WebUntisCredentials
    ) -> config_entries.FlowResult | None:
        """
        Testet die Credentials und legt – bei Erfolg – den ConfigEntry an.

        Liefert None bei Authentifizierungsfehler, damit der aufrufende
        Step seine Fehlermeldung zeigen kann.
        """
        session = async_get_clientsession(self.hass)
        client = WebUntisQRClient(creds, session)
        try:
            await client.async_get_user_data()
        except WebUntisAuthError as err:
            _LOGGER.warning("WebUntis-Login fehlgeschlagen: %s", err)
            return None
        except Exception:  # noqa: BLE001
            # Netz-/Server-Fehler unterscheiden wir hier nicht weiter
            _LOGGER.exception("Unerwarteter Fehler beim WebUntis-Login")
            return None

        # Eindeutige unique_id pro Konto verhindert Doppel-Einträge
        unique_id = f"{creds.server}::{creds.school}::{creds.user}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"WebUntis – {creds.user}@{creds.school}",
            data={
                CONF_SERVER: creds.server,
                CONF_SCHOOL: creds.school,
                CONF_USER: creds.user,
                CONF_KEY: creds.key,
                CONF_SCHOOL_NUMBER: creds.school_number,
            },
            options={
                # Defaults beim Anlegen direkt setzen, damit der User sie
                # im UI hochzählen / senken kann.
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_LOOKAHEAD_DAYS: DEFAULT_LOOKAHEAD_DAYS,
            },
        )


class WebUntisOptionsFlow(config_entries.OptionsFlow):
    """
    Options-Dialog: erlaubt das Ändern von Polling-Intervall und Lookahead-Tagen
    nachdem die Integration eingerichtet ist – ohne Re-Auth / QR-Code-Re-Scan.
    """

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if user_input is not None:
            # Werte sind durch das Schema bereits geclamped/validiert
            return self.async_create_entry(title="", data=user_input)

        # Aktuelle Werte als Vorbelegung (entweder Options oder Default)
        current_scan = self._entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        current_lookahead = self._entry.options.get(
            CONF_LOOKAHEAD_DAYS, DEFAULT_LOOKAHEAD_DAYS
        )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL, default=current_scan
                ): vol.All(int, vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
                vol.Required(
                    CONF_LOOKAHEAD_DAYS, default=current_lookahead
                ): vol.All(
                    int, vol.Range(min=MIN_LOOKAHEAD_DAYS, max=MAX_LOOKAHEAD_DAYS)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
