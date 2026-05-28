# Brand-Assets

Hier liegt das Projekt-Icon als SVG (`icon.svg`).

## Für die Anzeige in Home Assistant

Damit HA das Icon in *Einstellungen → Geräte & Dienste* neben dem
Integration-Eintrag anzeigt, muss es in das offizielle Brands-Repo:

1. Aus `icon.svg` zwei PNGs rendern:
   - `icon.png` 256×256 (z. B. via Inkscape/Online-Konverter)
   - `icon@2x.png` 512×512
2. Fork von <https://github.com/home-assistant/brands>
3. Dateien ablegen unter:
   ```
   custom_integrations/webuntis_qr/icon.png
   custom_integrations/webuntis_qr/icon@2x.png
   custom_integrations/webuntis_qr/logo.png        (optional, 256×256+)
   custom_integrations/webuntis_qr/logo@2x.png     (optional, 512×512+)
   ```
4. PR aufmachen. Nach Merge ist das Icon automatisch in HA verfügbar
   (kein Update der Integration nötig – HA lädt von brands.home-assistant.io).

## Entity-Icons

Die Icons für die einzelnen Sensoren / Binary-Sensoren / den Kalender
werden bereits über `custom_components/webuntis_qr/icons.json` gesetzt
(HA-Translation-Icon-Mechanismus, ab Core 2024.2). Dafür sind keine
Brands-Repo-Einträge nötig.
