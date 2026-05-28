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

# Standard-Polling-Intervall in Sekunden (5 min – WebUntis ist nicht real-time)
DEFAULT_SCAN_INTERVAL = 300

# Plattformen, die diese Integration registriert
PLATFORMS = ["sensor", "calendar"]
