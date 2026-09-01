# WebUntis (QR Login) for Home Assistant

[Deutsche Version / German version](README.de.md)

Custom integration that signs in to **WebUntis** with the QR code from the Untis
mobile app and exposes the timetable in Home Assistant as sensors, a binary
sensor and a calendar. No WebUntis password is required, the login uses the TOTP
secret contained in the QR code, exactly like the official mobile app does.

- Installable through HACS
- Timetable calendar for Lovelace calendar cards and automations
- Sensors for the next lesson, the current lesson, today's lesson count and the
  next school holidays
- Binary sensor that fires when the timetable changed (cancellation,
  substitution, room change, extra lesson)

## Requirements

- Home Assistant **2026.3** or newer. The integration ships its brand icons
  inside `custom_components/webuntis_qr/brand/`, and Home Assistant only reads
  those from 2026.3 onwards. On older versions the integration would show no
  icon at all.
- A WebUntis account that may create a mobile access QR code
  (Untis app: *Profile - Sharing - Access via mobile device*).
- The dependency `pyotp` is installed automatically by Home Assistant.

## Installation

### HACS (recommended)

1. HACS, three dot menu, **Custom repositories**
2. Add `https://github.com/NiklasM-foss/ha-webuntis-qr`, category *Integration*
3. Install "WebUntis (QR-Login)" and restart Home Assistant
4. *Settings, Devices & services, Add integration, WebUntis (QR-Login)*

### Manual

1. Copy the folder `custom_components/webuntis_qr/` into your configuration
   directory so that it ends up as `<config>/custom_components/webuntis_qr/`.
2. Restart Home Assistant.
3. Add the integration through the UI as described above.

## Setup

The config flow offers two ways in.

**Paste QR code content (recommended)**

1. In the Untis app open *Profile, Sharing, Access via mobile device*.
2. Scan the QR code shown there with a second device, for example the phone
   camera app, which displays the decoded `untis://setschool?...` text.
3. Paste the complete text into the dialog.

The QR payload has this shape:

```
untis://setschool?url=<server>&school=<school>&user=<username>&key=<base32-secret>&schoolNumber=<n>
```

**Manual entry**

If the QR route is not available, enter server, school, user and key by hand.
These are the same values, the key being the Base32 TOTP secret.

Both paths validate the credentials against the school server before the config
entry is created, so a typo is reported right away instead of failing later.

### Options

*Settings, Devices & services, WebUntis (QR-Login), Configure*

| Option | Range | Default | Meaning |
| --- | --- | --- | --- |
| Update interval | 60 to 3600 seconds | 300 | How often the timetable is polled. Lower means fresher data and more load on the school server. |
| Lookahead | 1 to 60 days | 7 | How many days of timetable are fetched, starting today. |

Changing an option reloads the integration automatically, the QR code does not
have to be scanned again.

## Entities

One device is created per configured account, holding six entities. Entity names
come from the translation files and therefore follow the language of your Home
Assistant instance. The names below are the English ones.

| Entity | Platform | State |
| --- | --- | --- |
| Next lesson | `sensor` | Subject of the next lesson that is not cancelled, `unknown` if the lookahead window holds none |
| Current lesson | `sensor` | Subject of the lesson running right now, `frei` when nothing is running, `<subject> (entfällt)` when the running lesson is cancelled |
| Lessons today | `sensor` | Number of today's lessons, cancelled ones excluded, unit `Stunden` |
| Next holiday | `sensor` | Days until the next holiday period, unit `Tage`, `0` while a holiday is running |
| Changes since last update | `binary_sensor` | `on` for exactly the refresh cycle in which the timetable content changed, back to `off` afterwards |
| Timetable | `calendar` | All lessons in the lookahead window |

### Attributes

**Next lesson**: `start`, `end`, `room`, `teacher`, `subject_long`

**Current lesson**: `room`, `teacher`, `end`, `cancelled`

**Lessons today**: `first_start`, `last_end`, `cancelled_count`, `subjects`.
Cancelled lessons are part of these attributes, only the state excludes them.

**Next holiday**: `name`, `long_name`, `start_date`, `end_date`, `is_active`,
`duration_days`. The source is `masterData.holidays`, which covers both multi
day school holidays and single days off. `end_date` is inclusive.

**Changes since last update**: `fingerprint` (SHA-256 over the current periods),
`last_update`

**Timetable**: calendar events use the summary `Subject • Room`, prefixed with
`[entfällt]` when the lesson is cancelled. The room is also set as `location`,
while teacher, long subject name and room go into the description.

### Entity IDs

An entity ID is built once, when the entity is first created, from the config
entry title and the entity name in the language active at that moment, for
example `sensor.webuntis_<user>_<school>_next_lesson`. It is then kept in the
entity registry and does not change afterwards, so an installation that was set
up in German keeps its German entity IDs. Look the exact IDs up under *Settings,
Devices & services, Entities*, where they can also be renamed to something
shorter.

## What is stored

The config entry keeps the server, the school name, **the username** and **the
TOTP shared secret** from the QR code, plus the optional school number. No
WebUntis password is asked for at any point and none is stored.

The TOTP shared secret is long lived and functionally a credential, though:
anyone holding it can sign in to that Untis account for as long as the access
stays valid. Like every config entry it is stored in plain text inside
`<config>/.storage/core.config_entries`, so treat backups and snapshots of the
configuration directory accordingly. Revoking the mobile access in the Untis app
(*Profile, Sharing*) invalidates the secret and with it this integration's login.

## Example automations

Notify when the timetable changed:

```yaml
alias: WebUntis timetable changed
triggers:
  - trigger: state
    entity_id: binary_sensor.webuntis_changes_since_last_update
    to: "on"
actions:
  - action: notify.mobile_app_phone
    data:
      title: "Timetable changed"
      message: >
        {{ states('sensor.webuntis_lessons_today') }} lessons today,
        next up: {{ states('sensor.webuntis_next_lesson') }}
```

Morning briefing before school starts:

```yaml
alias: WebUntis morning briefing
triggers:
  - trigger: time
    at: "06:50:00"
conditions:
  - condition: numeric_state
    entity_id: sensor.webuntis_lessons_today
    above: 0
actions:
  - action: notify.mobile_app_phone
    data:
      title: "Today: {{ states('sensor.webuntis_lessons_today') }} lessons"
      message: >
        Starts at
        {{ as_timestamp(state_attr('sensor.webuntis_lessons_today', 'first_start'))
           | timestamp_custom('%H:%M') }},
        first subject: {{ states('sensor.webuntis_next_lesson') }}
```

Replace the entity IDs with the ones your installation actually created, see
*Entity IDs* above.

## Troubleshooting

**"Login failed" while adding the integration.** Usually the pasted text is
incomplete, it needs at least `url`, `school`, `user` and `key`. Check as well
whether the mobile access was revoked in the Untis app, in which case a new QR
code has to be generated. TOTP depends on the clock, so the time of the Home
Assistant host must be accurate to within roughly half a minute.

**Setup works, but no lessons show up.** Look for `Keine elemId in userData` in
the log, which means the account has no timetable element attached, and try a
larger lookahead window in the options.

**Lessons appear shifted by a couple of hours.** WebUntis returns the local
school wall clock time but appends `Z`. Since 1.3.1 the integration reads it as
Home Assistant local time, so make sure the Home Assistant time zone matches the
one of the school.

**No icon for the integration.** The brand icons require Home Assistant 2026.3
or newer, see Requirements.

**More detail in the log:**

```yaml
logger:
  logs:
    custom_components.webuntis_qr: debug
```

## Repository layout

```
custom_components/webuntis_qr/
├── __init__.py          # setup entry point, config entry loader
├── api.py               # JSON-RPC client with TOTP auth and QR parser
├── binary_sensor.py     # binary sensor: changes since last update
├── calendar.py          # calendar platform (timetable)
├── config_flow.py       # config flow (QR / manual) and options flow
├── const.py             # domain, config keys, defaults, platform list
├── coordinator.py       # DataUpdateCoordinator, polling and caching
├── icons.json           # entity icons
├── manifest.json        # integration manifest
├── sensor.py            # sensors: next lesson, current lesson, lessons today, next holiday
├── strings.json         # UI strings, source for the translations
├── brand/               # integration icons, read by Home Assistant 2026.3+
│   ├── icon.png
│   ├── icon.svg
│   └── icon@2x.png
└── translations/
    ├── de.json
    └── en.json
.github/workflows/validate.yml   # hassfest and HACS validation
hacs.json                        # HACS metadata
LICENSE                          # MIT
README.md                        # this file
README.de.md                     # German version
```

## Changelog

- **1.5.0** Documentation rewritten: English `README.md` plus German
  `README.de.md`, with a complete and correct entity list, an explicit note on
  what the config entry stores, and a troubleshooting section. Entity names are
  no longer hard coded in German, they come from the translation files now, and
  the binary sensor and the calendar got their missing translations.
- **1.4.1** Minimum Home Assistant version raised to 2026.3, which is when the
  core started reading brand icons shipped inside an integration. Removed the
  outdated instructions for submitting icons to `home-assistant/brands`, that
  repository no longer accepts custom integrations, together with the redundant
  top level brand directory.
- **1.4.0** New sensor for the next holiday: days until the next holiday period
  from `masterData.holidays`, `0` while a holiday is running, name, range and
  duration as attributes.
- **1.3.1** Time zone fix. WebUntis puts the local school wall clock time into
  `startDateTime`/`endDateTime` but appends `Z`, which used to be read as UTC
  and shifted every lesson by the UTC offset.
- **1.3.0** Project icon plus `icons.json` for entity icons, including a dynamic
  bell icon on the change binary sensor.
- **1.2.1** Room shown in the calendar title (`Subject • Room`), still also in
  `location` and in the description.
- **1.2.0** Binary sensor for timetable changes, based on a SHA-256 fingerprint
  over the periods.
- **1.1.0** Options flow for update interval (60 to 3600 s) and lookahead window
  (1 to 60 days), with automatic reload.
- **1.0.2** Period parsing corrected, `startDateTime`/`endDateTime` are ISO
  strings and `is` is a list of status tags. Datetimes are timezone aware.
- **1.0.1** Fixes against a real Untis server: `params` as array, `v=i3.2` in the
  endpoint, `type` as string, element read from `elemId`/`elemType`.
- **1.0.0** Initial release: QR login, TOTP auth, sensors and calendar, own async
  JSON-RPC client without `python-webuntis`.

## Notes and limitations

- The integration talks to the internal mobile API
  (`/WebUntis/jsonrpc_intern.do`). School servers differ in the fields they
  return, so if something is missing please open an issue including the log
  output.
- Read only, the integration never writes anything back to WebUntis.
- There is no homework entity. The integration covers the timetable, lesson
  counters, holidays and change detection, nothing else.

## License

MIT, see [LICENSE](LICENSE).
