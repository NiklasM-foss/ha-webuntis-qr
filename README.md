# WebUntis (QR-Login) – Home Assistant Integration

HACS-kompatible Custom-Integration, die sich per **QR-Code aus der Untis-App** bei
WebUntis anmeldet und den Stundenplan als Sensoren + Kalender in Home Assistant
verfügbar macht – ohne WebUntis-Passwort.

## Status

Version 1.4.1 – funktionsfähig, ohne externe `python-webuntis`-Dependency
(eigener async JSON-RPC-Client + TOTP). Verschiedene Schul-Server können
leicht unterschiedliche Felder liefern; bei Problemen Issue öffnen.

## Stack

- Home Assistant ≥ 2026.3
- Python (asyncio + aiohttp)
- pyotp für TOTP-Generierung
- HACS (Repo-Typ: Integration)

## Verzeichnisstruktur

```
custom_components/webuntis_qr/
├── __init__.py          # Setup-Einstiegspunkt, ConfigEntry-Loader
├── api.py               # JSON-RPC-Client mit TOTP-Auth + QR-Parser
├── binary_sensor.py     # Binary-Sensor: Änderungen seit letzter Aktualisierung
├── calendar.py          # Calendar-Plattform (Stundenplan als HA-Kalender)
├── config_flow.py       # UI-Anmeldedialog (QR / manuell)
├── const.py             # Konstanten (DOMAIN, Config-Keys)
├── coordinator.py       # DataUpdateCoordinator – Polling + Caching
├── icons.json           # Entity-Icons (HA-Translation-Icon-Mechanismus)
├── manifest.json        # HA-Manifest
├── sensor.py            # Sensoren: nächste/aktuelle Stunde, Stunden heute, nächste Ferien
├── strings.json         # UI-Strings (Quelle für Übersetzungen)
├── brand/               # Integration-Icon (icon.png, icon@2x.png, icon.svg)
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
- HA speichert Benutzername und Secret im ConfigEntry. Ein WebUntis-Passwort
  wird nie abgefragt, das dauerhaft gültige TOTP-Secret ist aber wie ein
  Zugangsdatum zu behandeln: Wer es hat, kommt an das Untis-Konto. Wird der
  Zugang in der Untis-App widerrufen, ist auch dieses Secret wertlos.

## Installation

### Via HACS (empfohlen)

1. HACS → Drei-Punkte-Menü → **Benutzerdefinierte Repositories**
2. URL `https://github.com/NiklasM-foss/ha-webuntis-qr` eintragen,
   Kategorie *Integration*
3. „WebUntis (QR-Login)" installieren, Home Assistant neu starten
4. *Einstellungen → Geräte & Dienste → Integration hinzufügen → WebUntis (QR-Login)*

### Manuell

1. Inhalt von `custom_components/webuntis_qr/` ins HA-Configdir kopieren:
   ```
   <ha-config>/custom_components/webuntis_qr/
   ```
2. Home Assistant neu starten.
3. Integration über die UI hinzufügen (siehe oben).

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
- `sensor.<konto>_naechste_ferien` – Tage bis zu den nächsten Ferien /
  beweglichen Ferientagen (Quelle: `masterData.holidays`). Wert `0` während
  laufender Ferien. Attribute: `name`, `long_name`, `start_date`, `end_date`,
  `is_active`, `duration_days`.
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

- 1.4.1 – Mindestversion auf Home Assistant 2026.3 angehoben, weil die
  mitgelieferten Brand-Icons (`custom_components/webuntis_qr/brand/`) erst ab
  dieser Version gelesen werden. Die veraltete Anleitung zum Brands-Repo
  entfernt – seit 2026.3 nimmt `home-assistant/brands` keine Custom-Integrationen
  mehr auf, die Icons im Repo sind der vorgesehene Weg. Doku korrigiert:
  Versionsangabe, Verzeichnisbaum und die Aussage zu gespeicherten Zugangsdaten.
- 1.4.0 – Neuer Sensor „Nächste Ferien" (`sensor.<konto>_naechste_ferien`):
  Tage bis zu den nächsten Ferien/beweglichen Ferientagen aus
  `masterData.holidays`. `0` während laufender Ferien; Name, Zeitraum und
  Dauer als Attribute.
- 1.3.1 – **Zeitzonen-Bug behoben**: WebUntis liefert in `startDateTime`/
  `endDateTime` die lokale Schul-Wandzeit, hängt aber fälschlich „Z" (UTC) an.
  Bisher wurde das als UTC interpretiert, wodurch Stunden in HA um den
  UTC-Offset verschoben erschienen (z. B. 07:40 → 09:40 in CEST). Jetzt wird
  die Wandzeit als HA-Lokalzeit interpretiert.
- 1.3.0 – Eigenes Projekt-Icon (Doktorhut + QR-Marker) + `icons.json` für
  Entity-Icons (HA-Translation-Mechanismus, dynamisches Glocken-Icon beim
  Änderungs-Sensor on/off).
- 1.2.1 – Raum erscheint jetzt im Kalender-Titel (Format „Fach • Raum"),
  zusätzlich weiterhin in `location` und Beschreibung.
- 1.2.0 – Binary-Sensor „Änderungen seit letzter Aktualisierung" hinzugefügt
  (SHA-256-Fingerprint über Periods – wird für einen Refresh-Zyklus true
  wenn sich Stundenplan-Inhalte geändert haben, danach automatisch false).
- 1.1.0 – Options-Flow: Aktualisierungsintervall (60–3600 s, Default 300 s)
  und Lookahead-Zeitraum (1–60 Tage, Default 7) im UI einstellbar
  (*Integration → Konfigurieren*). Reload erfolgt automatisch.
- 1.0.2 – Period-Parsing korrigiert: `startDateTime`/`endDateTime` sind
  ISO-Strings („2026-05-28T11:10Z"), nicht Integer. `is` ist eine Liste
  („CANCELLED" als Tag), nicht ein Dict. Datetimes jetzt timezone-aware.
- 1.0.1 – Fix gegen echten Untis-Server: `params` als Array, `v=i3.2` im
  Endpoint, `type` als String ("STUDENT"), Lesen von `elemId`/`elemType`
  aus `userData` (statt `personId`). Verifiziert gegen bk-luebbecke.
- 1.0.0 – Initiale Release: QR-Login, TOTP-Auth, Sensoren + Kalender,
  eigener async JSON-RPC-Client (kein `python-webuntis`).

## Lizenz

MIT
