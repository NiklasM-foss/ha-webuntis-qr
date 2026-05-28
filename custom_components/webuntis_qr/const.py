# Zentrale Konstanten der WebUntis-QR-Integration.
# Wird von allen anderen Modulen importiert, damit Domain-Name, Config-Keys
# und Default-Intervalle nur an einer Stelle gepflegt werden müssen.

from __future__ import annotations

# Eindeutige Domain der Integration (taucht in entity_ids als Prefix auf)
DOMAIN = "webuntis_qr"

# Schlüssel im ConfigEntry / im QR-Payload
CONF_SERVER = "server"            # z.B. "ajax.webuntis.com"
CONF_SCHOOL = "school"            # interner Schulname (URL-encoded)
CONF_USER = "user"                # WebUntis-Anmeldename
CONF_KEY = "key"                  # TOTP-Shared-Secret aus dem QR-Code (Base32)
CONF_SCHOOL_NUMBER = "schoolNumber"  # optional, manche Schulen liefern das mit

# Options-Keys (entry.options) – zur Laufzeit über den UI-Optionsdialog änderbar
CONF_SCAN_INTERVAL = "scan_interval"      # Polling-Intervall in Sekunden
CONF_LOOKAHEAD_DAYS = "lookahead_days"    # Wie viele Tage Stundenplan im Voraus laden

# Defaults – greifen, solange der User keine Options gesetzt hat
DEFAULT_SCAN_INTERVAL = 300               # 5 Minuten
DEFAULT_LOOKAHEAD_DAYS = 7                # eine Schulwoche

# Sicherheits-Grenzen, damit nicht versehentlich der Untis-Server gehämmert wird
MIN_SCAN_INTERVAL = 60                    # max. einmal pro Minute
MAX_SCAN_INTERVAL = 3600                  # mind. einmal pro Stunde
MIN_LOOKAHEAD_DAYS = 1
MAX_LOOKAHEAD_DAYS = 60

# Plattformen, die diese Integration registriert
PLATFORMS = ["sensor", "calendar"]
