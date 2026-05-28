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
   - Owner: `NiklasM-foss`
5. **Publish repository**

## 2. Tag v1.0.0 mit hochpushen

GitHub Desktop pusht Tags nicht automatisch. Im Terminal (in diesem Ordner):
```
git push origin v1.0.0
```

## 3. Repo-Settings auf github.com

Repo öffnen → **About** (Zahnrad rechts oben) → **Topics** setzen:
```
home-assistant  hacs  hacs-integration  webuntis  untis  qr-login  home-assistant-integration
```

## 4. GitHub Release erstellen

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

## 5. Aufräumen

- Diese Datei (`PUBLISH_TO_GITHUB.md`) löschen, committen, pushen.

## Optional: Gitea-Mirror weiter pflegen

Der Gitea-Remote heißt jetzt `gitea` (statt `origin`). Doppel-Push:
```
git push origin main      # GitHub
git push gitea main       # Gitea
```
