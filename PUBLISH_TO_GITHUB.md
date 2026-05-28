# GitHub-Publish-Checkliste

Diese Datei ist nur für dich – nach erfolgreichem Publish bitte löschen.

## 1. In GitHub Desktop

1. **File → Add local repository…**
2. Pfad: `C:\Users\nikla\projects\ha-webuntis-qr`
3. Oben in der Leiste erscheint **"Publish repository"** → klicken
4. Dialog:
   - **Name:** `ha-webuntis-qr`
   - **Description:** `HACS-kompatible Home Assistant Integration für WebUntis mit QR-Code-Login (TOTP)`
   - **Keep this code private:** ❌ AUS (Public)
   - Owner: dein User
5. **Publish repository**

## 2. Tag mit hochpushen

GitHub Desktop pusht Tags nicht automatisch. Entweder:

- **GitHub Desktop:** Menüleiste → **Repository → Push** (Tags werden mitgenommen wenn beim Pushen "include tags" auftaucht), oder
- **Im Terminal** (in diesem Ordner):
  ```
  git push origin v1.0.0
  ```

## 3. Username im Code ersetzen

In zwei Dateien stehen Platzhalter `YOUR-GITHUB-USERNAME`:

- `custom_components/webuntis_qr/manifest.json` (documentation, issue_tracker, codeowners)
- `README.md` (HACS-URL)

Such-und-Ersetzen über die ganzen Files (z.B. in VS Code: Strg+Shift+H):
```
YOUR-GITHUB-USERNAME  →  <dein GitHub-User>
```
Danach in GitHub Desktop committen + pushen.

## 4. Repo-Settings auf github.com

Im neu erstellten Repo:

- **About** (Zahnrad rechts oben) → **Topics** setzen:
  ```
  home-assistant  hacs  hacs-integration  webuntis  untis  qr-login  home-assistant-integration
  ```
  (HACS findet das Repo über diese Topics besser; siehe HACS-Doku.)

## 5. GitHub Release erstellen

HACS braucht ein **Release**, nicht nur einen Tag.

- Repo-Seite → rechts **Releases** → **Draft a new release**
- **Choose a tag:** `v1.0.0` (existiert bereits)
- **Release title:** `v1.0.0`
- **Notes:**
  ```
  Initiale Release.

  - QR-Code-Login (TOTP, kein Username/Passwort)
  - Sensoren: nächste Stunde, aktuelle Stunde, Stunden heute
  - Calendar-Entity mit Stundenplan
  - Eigener async JSON-RPC-Client, keine python-webuntis-Dependency
  ```
- **Publish release**

## 6. Aufräumen

- Diese Datei (`PUBLISH_TO_GITHUB.md`) löschen + committen.

## Optional: Gitea-Mirror weiter pflegen

Der Gitea-Remote heißt jetzt `gitea` (statt `origin`). Doppel-Push:
```
git push origin main      # GitHub
git push gitea main       # Gitea
```
