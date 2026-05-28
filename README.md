# WebUntis (QR-Login) – Home Assistant Integration

HACS-kompatible Custom-Integration, die sich per **QR-Code aus der Untis-App** bei
WebUntis anmeldet und den Stundenplan als Sensoren + Kalender in Home Assistant
verfügbar macht – ohne Username/Passwort.

## Status

Version 1.0.0 – funktionsfähig, ohne externe `python-webuntis`-Dependency
(eigener async JSON-RPC-Client + TOTP). Verschiedene Schul-Server können
leicht unterschiedliche Felder liefern; bei Problemen Issue öffnen.

## Stack

- Home Assistant ≥ 2024.4
- Python (asyncio + aiohttp)
- pyotp für TOTP-Generierung
- HACS (Repo-Typ: Integration)

## Verzeichnisstruktur

```
custom_components/webuntis_qr/
├── __init__.py          # Setup-Einstiegspunkt, ConfigEntry-Loader
├── api.py               # JSON-RPC-Client mit TOTP-Auth + QR-Parser
├── calendar.py          # Calendar-Plattform (Stundenplan als HA-Kalender)
├── config_flow.py       # UI-Anmeldedialog (QR / manuell)
├── const.py             # Konstanten (DOMAIN, Config-Keys)
├── coordinator.py       # DataUpdateCoordinator – Polling + Caching
├── manifest.json        # HA-Manifest
├── sensor.py            # Sensoren: nächste/aktuelle Stunde, Stunden heute
├── strings.json         # UI-Strings (Quelle für Übersetzungen)
└── translations/
    ├── de.json
    └── en.json
hacs.json                # HACS-Metadaten
README.md
```

## QR-Code-Login

Der QR-Code in der Untis-App (Profil → Freigaben → **Zugang über Smartphone**)
enthält eine URI in der Form:

```
untis://setschool?url=<server>&school=<schulname>&user=<username>&key=<base32-secret>&schoolNumber=<n>
```

- `key` ist ein TOTP-Shared-Secret (RFC 6238, 30 s Schritte, 6 Ziffern).
- Beim Login wird aus `key` der aktuelle 6-stellige Code erzeugt und im
  `auth`-Block des JSON-RPC-Aufrufs an `https://<server>/WebUntis/jsonrpc_intern.do`
  mitgeschickt – exakt wie es die offizielle Mobile-App tut.
- HA speichert das Secret im ConfigEntry; danach werden keine Passwörter benötigt.

## Installation

> **Hinweis:** HACS kommuniziert ausschließlich mit der GitHub-API – ein
> selbst gehosteter Gitea-Server (wie dieser hier) lässt sich **nicht** als
> Custom Repository in HACS eintragen. Solange das Repo nur auf Gitea liegt,
> bitte manuell installieren. Wird das Repo später nach GitHub gespiegelt,
> wird es HACS-fähig (`hacs.json` + `manifest.json` sind bereits konform).

### Manuell (Standardweg auf diesem Setup)

1. Inhalt von `custom_components/webuntis_qr/` ins HA-Configdir kopieren:
   ```
   <ha-config>/custom_components/webuntis_qr/
   ```
   Beispiel via `pscp` (Windows → HA-Host):
   ```
   pscp -pw <pw> -r custom_components/webuntis_qr root@<ha-host>:/config/custom_components/
   ```
2. Home Assistant neu starten.
3. *Einstellungen → Geräte & Dienste → Integration hinzufügen → WebUntis (QR-Login)*.

### Via HACS (nur wenn auf GitHub gespiegelt)

Wenn das Repo zusätzlich auf GitHub veröffentlicht wurde:

1. HACS → Drei-Punkte-Menü → **Benutzerdefinierte Repositories**
2. GitHub-URL eintragen, Kategorie *Integration*
3. Installieren, HA neu starten.

### HACS-Konformität (für späteren GitHub-Push)

Bereits erfüllt:
- `hacs.json` mit `name`, `homeassistant`, `country`, `render_readme`
- `manifest.json` mit `domain`, `documentation`, `issue_tracker`, `codeowners`,
  `name`, `version`, `config_flow`, `iot_class`, `requirements`
- README mit Doku

Beim GitHub-Push noch zu tun:
- Repo-**Description** setzen
- **Topics** setzen: `home-assistant`, `hacs`, `hacs-integration`,
  `webuntis`, `untis`, `qr-login`, `home-assistant-integration`
- **Release** (nicht nur Tag) für jede Version anlegen – HACS nutzt den
  Release-Tag-Namen als Versions-String.

## Einrichtung

1. *Einstellungen → Geräte & Dienste → Integration hinzufügen → WebUntis (QR-Login)*
2. **QR-Code-Text einfügen** wählen
3. Auf einem zweiten Gerät (Handy) den Untis-QR-Code scannen (z. B. mit der
   Kamera-App – diese zeigt den `untis://...`-Text als kopierbares Banner).
4. Den kompletten Text einfügen → fertig.

Alternative: *Manuell* eingeben, wenn die Felder bereits einzeln bekannt sind.

## Entitäten

Pro Konto werden angelegt:

- `sensor.<konto>_naechste_stunde` – Fach der nächsten anstehenden Stunde
  (Attribute: Start, Ende, Raum, Lehrer, langer Fachname).
- `sensor.<konto>_aktuelle_stunde` – Fach, das gerade läuft, sonst `frei`.
- `sensor.<konto>_stunden_heute` – Anzahl heutiger Stunden (Ausfall exkl.).
- `calendar.<konto>_stundenplan` – Stundenplan-Kalender für Lovelace.

## Beispiel-Automation

```yaml
# 10 Minuten vor Schulbeginn Bescheid sagen
alias: Untis – Morgen-Briefing
trigger:
  - platform: time
    at: "06:50:00"
action:
  - service: notify.mobile_app_phone
    data:
      title: "Heute: {{ states('sensor.webuntis_stunden_heute') }} Stunden"
      message: >
        Start: {{ state_attr('sensor.webuntis_stunden_heute', 'first_start') }}
        – Erstes Fach: {{ states('sensor.webuntis_naechste_stunde') }}
```

## Letzte Änderungen

- 1.0.0 – Initiale Release: QR-Login, TOTP-Auth, Sensoren + Kalender,
  eigener async JSON-RPC-Client (kein `python-webuntis`).

## Lizenz

MIT
