# WebUntis (QR-Login) für Home Assistant

[English version / englische Version](README.md)

Custom-Integration, die sich mit dem QR-Code aus der Untis-App bei **WebUntis**
anmeldet und den Stundenplan in Home Assistant als Sensoren, Binary-Sensor und
Kalender bereitstellt. Ein WebUntis-Passwort wird nicht gebraucht, die Anmeldung
läuft über das TOTP-Secret aus dem QR-Code, genau wie in der offiziellen
Mobile-App.

- Über HACS installierbar
- Stundenplan-Kalender für Lovelace-Kalenderkarten und Automationen
- Sensoren für nächste Stunde, aktuelle Stunde, Stunden heute und die nächsten
  Ferien
- Binary-Sensor, der anschlägt, wenn sich der Stundenplan geändert hat (Ausfall,
  Vertretung, Raumwechsel, Zusatzstunde)

## Voraussetzungen

- Home Assistant **2026.3** oder neuer. Die Integration liefert ihre Brand-Icons
  in `custom_components/webuntis_qr/brand/` mit, und Home Assistant liest die
  erst ab 2026.3. Auf älteren Versionen bliebe die Integration ohne Icon.
- Ein WebUntis-Konto, das einen QR-Code für den mobilen Zugang erzeugen darf
  (Untis-App: *Profil, Freigaben, Zugang über Smartphone*).
- Die Abhängigkeit `pyotp` installiert Home Assistant automatisch.

## Installation

### HACS (empfohlen)

1. HACS, Drei-Punkte-Menü, **Benutzerdefinierte Repositories**
2. `https://github.com/NiklasM-foss/ha-webuntis-qr` eintragen, Kategorie
   *Integration*
3. „WebUntis (QR-Login)" installieren, Home Assistant neu starten
4. *Einstellungen, Geräte & Dienste, Integration hinzufügen, WebUntis
   (QR-Login)*

### Manuell

1. Den Ordner `custom_components/webuntis_qr/` ins Config-Verzeichnis kopieren,
   sodass er als `<config>/custom_components/webuntis_qr/` liegt.
2. Home Assistant neu starten.
3. Integration wie oben beschrieben über die UI hinzufügen.

## Einrichtung

Der Config-Flow bietet zwei Wege an.

**QR-Code-Text einfügen (empfohlen)**

1. In der Untis-App *Profil, Freigaben, Zugang über Smartphone* öffnen.
2. Den dort gezeigten QR-Code mit einem zweiten Gerät scannen, zum Beispiel mit
   der Handy-Kamera-App, die den dekodierten `untis://setschool?...`-Text
   anzeigt.
3. Den kompletten Text in den Dialog einfügen.

Der QR-Inhalt sieht so aus:

```
untis://setschool?url=<server>&school=<schule>&user=<benutzer>&key=<base32-secret>&schoolNumber=<n>
```

**Manuelle Eingabe**

Falls der QR-Weg nicht klappt, lassen sich Server, Schule, Benutzer und Key
einzeln eintragen. Es sind dieselben Werte, der Key ist das Base32-TOTP-Secret.

Beide Wege prüfen die Anmeldedaten gegen den Schul-Server, bevor der ConfigEntry
angelegt wird. Ein Tippfehler fällt also sofort auf und nicht erst später.

### Optionen

*Einstellungen, Geräte & Dienste, WebUntis (QR-Login), Konfigurieren*

| Option | Bereich | Standard | Bedeutung |
| --- | --- | --- | --- |
| Aktualisierungsintervall | 60 bis 3600 Sekunden | 300 | Wie oft der Stundenplan abgefragt wird. Kleiner heißt aktueller, aber mehr Last auf dem Schul-Server. |
| Vorausschau | 1 bis 60 Tage | 7 | Wie viele Tage Stundenplan ab heute geladen werden. |

Eine geänderte Option lädt die Integration automatisch neu, der QR-Code muss
nicht erneut gescannt werden.

## Entitäten

Pro eingerichtetem Konto entsteht ein Gerät mit sechs Entitäten. Die Namen kommen
aus den Übersetzungsdateien und richten sich damit nach der Sprache der
Home-Assistant-Instanz. Unten stehen die deutschen Namen.

| Entität | Plattform | Zustand |
| --- | --- | --- |
| Nächste Stunde | `sensor` | Fach der nächsten nicht ausgefallenen Stunde, `unknown`, wenn im Vorausschau-Zeitraum keine mehr liegt |
| Aktuelle Stunde | `sensor` | Fach der gerade laufenden Stunde, `frei`, wenn nichts läuft, `<Fach> (entfällt)`, wenn die laufende Stunde ausfällt |
| Stunden heute | `sensor` | Anzahl der heutigen Stunden ohne Ausfälle, Einheit `Stunden` |
| Nächste Ferien | `sensor` | Tage bis zu den nächsten Ferien, Einheit `Tage`, `0` während laufender Ferien |
| Änderungen seit letzter Aktualisierung | `binary_sensor` | `on` für genau den Refresh-Zyklus, in dem sich der Stundenplan geändert hat, danach wieder `off` |
| Stundenplan | `calendar` | Alle Stunden im Vorausschau-Zeitraum |

### Attribute

**Nächste Stunde**: `start`, `end`, `room`, `teacher`, `subject_long`

**Aktuelle Stunde**: `room`, `teacher`, `end`, `cancelled`

**Stunden heute**: `first_start`, `last_end`, `cancelled_count`, `subjects`.
Ausgefallene Stunden stecken in diesen Attributen mit drin, nur der Zustand
klammert sie aus.

**Nächste Ferien**: `name`, `long_name`, `start_date`, `end_date`, `is_active`,
`duration_days`. Quelle ist `masterData.holidays`, dort stehen sowohl mehrtägige
Schulferien als auch einzelne bewegliche Ferientage. `end_date` ist der letzte
freie Tag, also inklusive.

**Änderungen seit letzter Aktualisierung**: `fingerprint` (SHA-256 über die
aktuellen Stunden), `last_update`

**Stundenplan**: Kalendereinträge haben den Titel `Fach • Raum`, bei Ausfall mit
`[entfällt]` davor. Der Raum steht zusätzlich in `location`, Lehrer, langer
Fachname und Raum stehen in der Beschreibung.

### Entity-IDs

Eine Entity-ID entsteht einmalig beim ersten Anlegen der Entität, aus dem Titel
des ConfigEntry und dem Entitätsnamen in der damals aktiven Sprache, zum Beispiel
`sensor.webuntis_<benutzer>_<schule>_nachste_stunde`. Danach steht sie in der
Entity-Registry und ändert sich nicht mehr, eine auf Englisch eingerichtete
Installation behält also englische Entity-IDs. Die genauen IDs stehen unter
*Einstellungen, Geräte & Dienste, Entitäten* und lassen sich dort auch auf etwas
Kürzeres umbenennen.

## Was gespeichert wird

Der ConfigEntry enthält Server, Schulname, **den Benutzernamen** und **das
TOTP-Shared-Secret** aus dem QR-Code, dazu die optionale Schulnummer. Ein
WebUntis-Passwort wird nie abgefragt und nicht gespeichert.

Das TOTP-Shared-Secret ist allerdings langlebig und faktisch ein Zugangsdatum:
Wer es hat, kommt an das Untis-Konto, solange der Zugang gültig bleibt. Es liegt
wie jeder ConfigEntry im Klartext in
`<config>/.storage/core.config_entries`, entsprechend sollten Backups und
Snapshots des Config-Verzeichnisses behandelt werden. Wird der mobile Zugang in
der Untis-App widerrufen (*Profil, Freigaben*), ist das Secret wertlos und diese
Integration kann sich nicht mehr anmelden.

## Beispiel-Automationen

Meldung, wenn sich der Stundenplan geändert hat:

```yaml
alias: WebUntis Stundenplan geändert
triggers:
  - trigger: state
    entity_id: binary_sensor.webuntis_anderungen_seit_letzter_aktualisierung
    to: "on"
actions:
  - action: notify.mobile_app_handy
    data:
      title: "Stundenplan geändert"
      message: >
        Heute {{ states('sensor.webuntis_stunden_heute') }} Stunden,
        als Nächstes: {{ states('sensor.webuntis_nachste_stunde') }}
```

Morgen-Briefing vor Schulbeginn:

```yaml
alias: WebUntis Morgen-Briefing
triggers:
  - trigger: time
    at: "06:50:00"
conditions:
  - condition: numeric_state
    entity_id: sensor.webuntis_stunden_heute
    above: 0
actions:
  - action: notify.mobile_app_handy
    data:
      title: "Heute: {{ states('sensor.webuntis_stunden_heute') }} Stunden"
      message: >
        Beginn
        {{ as_timestamp(state_attr('sensor.webuntis_stunden_heute', 'first_start'))
           | timestamp_custom('%H:%M') }} Uhr,
        erstes Fach: {{ states('sensor.webuntis_nachste_stunde') }}
```

Die Entity-IDs durch die der eigenen Installation ersetzen, siehe *Entity-IDs*
weiter oben.

## Fehlersuche

**„Anmeldung fehlgeschlagen" beim Hinzufügen.** Meist ist der eingefügte Text
unvollständig, gebraucht werden mindestens `url`, `school`, `user` und `key`.
Ebenfalls prüfen, ob der mobile Zugang in der Untis-App widerrufen wurde, dann
muss ein neuer QR-Code erzeugt werden. TOTP hängt an der Uhr, die Zeit des
Home-Assistant-Hosts muss also auf etwa eine halbe Minute genau stimmen.

**Einrichtung klappt, aber es tauchen keine Stunden auf.** Im Log nach
`Keine elemId in userData` schauen, das bedeutet, dass am Konto kein
Stundenplan-Element hängt. Sonst hilft ein größerer Vorausschau-Zeitraum in den
Optionen.

**Stunden erscheinen um ein paar Stunden verschoben.** WebUntis liefert die
lokale Schul-Wandzeit, hängt aber „Z" an. Seit 1.3.1 wird das als
HA-Lokalzeit gelesen, die Zeitzone in Home Assistant muss also zu der der Schule
passen.

**Die Integration hat kein Icon.** Die Brand-Icons brauchen Home Assistant 2026.3
oder neuer, siehe Voraussetzungen.

**Mehr Details im Log:**

```yaml
logger:
  logs:
    custom_components.webuntis_qr: debug
```

## Verzeichnisstruktur

```
custom_components/webuntis_qr/
├── __init__.py          # Setup-Einstiegspunkt, ConfigEntry-Loader
├── api.py               # JSON-RPC-Client mit TOTP-Auth und QR-Parser
├── binary_sensor.py     # Binary-Sensor: Änderungen seit letzter Aktualisierung
├── calendar.py          # Kalender-Plattform (Stundenplan)
├── config_flow.py       # Config-Flow (QR / manuell) und Options-Flow
├── const.py             # Domain, Config-Keys, Defaults, Plattform-Liste
├── coordinator.py       # DataUpdateCoordinator, Polling und Caching
├── icons.json           # Entity-Icons
├── manifest.json        # HA-Manifest
├── sensor.py            # Sensoren: nächste Stunde, aktuelle Stunde, Stunden heute, nächste Ferien
├── strings.json         # UI-Strings, Quelle für die Übersetzungen
├── brand/               # Integrations-Icons, ab Home Assistant 2026.3 gelesen
│   ├── icon.png
│   ├── icon.svg
│   └── icon@2x.png
└── translations/
    ├── de.json
    └── en.json
.github/workflows/validate.yml   # hassfest- und HACS-Validierung
hacs.json                        # HACS-Metadaten
LICENSE                          # MIT
README.md                        # englische Version
README.de.md                     # diese Datei
```

## Änderungen

- **1.5.0** Doku neu geschrieben: englische `README.md` plus deutsche
  `README.de.md`, mit vollständiger und korrekter Entitätenliste, klarer Aussage
  dazu, was der ConfigEntry speichert, und einem Abschnitt zur Fehlersuche. Die
  Entitätsnamen stehen nicht mehr fest auf Deutsch im Code, sondern kommen aus
  den Übersetzungsdateien; Binary-Sensor und Kalender haben ihre fehlenden
  Übersetzungen bekommen.
- **1.4.1** Mindestversion auf Home Assistant 2026.3 angehoben, weil der Core
  erst ab da die in der Integration mitgelieferten Brand-Icons liest. Die
  veraltete Anleitung zum Einreichen bei `home-assistant/brands` entfernt, dieses
  Repository nimmt keine Custom-Integrationen mehr auf, dazu das überflüssige
  Brand-Verzeichnis auf oberster Ebene.
- **1.4.0** Neuer Sensor für die nächsten Ferien: Tage bis zum nächsten
  Ferienzeitraum aus `masterData.holidays`, `0` während laufender Ferien, Name,
  Zeitraum und Dauer als Attribute.
- **1.3.1** Zeitzonen-Fix. WebUntis schreibt die lokale Schul-Wandzeit in
  `startDateTime`/`endDateTime`, hängt aber „Z" an, was vorher als UTC gelesen
  wurde und jede Stunde um den UTC-Offset verschoben hat.
- **1.3.0** Projekt-Icon und `icons.json` für Entity-Icons, inklusive dynamischem
  Glocken-Icon am Änderungs-Binary-Sensor.
- **1.2.1** Raum im Kalender-Titel (`Fach • Raum`), weiterhin zusätzlich in
  `location` und in der Beschreibung.
- **1.2.0** Binary-Sensor für Stundenplan-Änderungen, auf Basis eines
  SHA-256-Fingerprints über die Stunden.
- **1.1.0** Options-Flow für Aktualisierungsintervall (60 bis 3600 s) und
  Vorausschau (1 bis 60 Tage), mit automatischem Reload.
- **1.0.2** Period-Parsing korrigiert, `startDateTime`/`endDateTime` sind
  ISO-Strings und `is` ist eine Liste von Status-Tags. Datetimes sind jetzt
  timezone-aware.
- **1.0.1** Fixes gegen einen echten Untis-Server: `params` als Array, `v=i3.2`
  im Endpoint, `type` als String, Element aus `elemId`/`elemType` gelesen.
- **1.0.0** Erste Version: QR-Login, TOTP-Auth, Sensoren und Kalender, eigener
  async JSON-RPC-Client ohne `python-webuntis`.

## Hinweise und Grenzen

- Die Integration spricht die interne Mobile-API
  (`/WebUntis/jsonrpc_intern.do`) an. Schul-Server liefern unterschiedliche
  Felder, wenn etwas fehlt also bitte ein Issue mit der Log-Ausgabe aufmachen.
- Nur lesend, es wird nie etwas nach WebUntis zurückgeschrieben.
- Es gibt keine Hausaufgaben-Entität. Abgedeckt sind Stundenplan,
  Stundenzähler, Ferien und Änderungserkennung, mehr nicht.

## Lizenz

MIT, siehe [LICENSE](LICENSE).
