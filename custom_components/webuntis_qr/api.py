"""
WebUntis Mobile-API Client mit TOTP-Authentifizierung.

Hintergrund: Der WebUntis-QR-Code enthält eine URI in der Form
    untis://setschool?url=<server>&school=<schoolName>&user=<username>&key=<TOTP-Secret>&schoolNumber=<n>

Im Gegensatz zur Browser-Anmeldung (Username/Password) nutzt die Mobile-App
einen TOTP-basierten Login: Aus dem `key` (Base32-Secret) wird per RFC6238
alle 30 s ein 6-stelliger Code erzeugt; diesen schickt man als `otp` an den
internen JSON-RPC-Endpoint `/WebUntis/jsonrpc_intern.do`.

Diese Datei kapselt sowohl die QR-URI-Parsing-Logik als auch den
authentifizierten Abruf des Stundenplans.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import pyotp
import aiohttp

_LOGGER = logging.getLogger(__name__)

# User-Agent: Untis-Server filtern Default-Python-UAs; wir geben uns als
# Mobile-Client aus, das matcht den offiziellen App-Flow.
USER_AGENT = "UntisMobileAndroid"

# API-Versions-Marker, den die Untis-Mobile-App auch mitschickt
API_VERSION = "i3.2"


@dataclass
class WebUntisCredentials:
    """Vom QR-Code geparste Anmeldedaten."""

    server: str          # Host ohne Schema, z.B. "ajax.webuntis.com"
    school: str          # interner Schulname
    user: str            # Anmeldename
    key: str             # TOTP-Secret (Base32)
    school_number: str | None = None


def parse_qr_payload(payload: str) -> WebUntisCredentials:
    """
    Parst die `untis://setschool?...` URI aus dem QR-Code.

    Wirft ValueError, wenn das Schema nicht passt oder Pflichtfelder fehlen.
    Akzeptiert auch reine Query-Strings (für Copy-Paste-Fälle ohne Schema).
    """
    payload = payload.strip()

    # Tolerant: User dürfen mit oder ohne Schema einfügen
    if not payload.startswith("untis://"):
        # Vielleicht nur der Query-Teil? Künstlich vervollständigen.
        if payload.startswith("?"):
            payload = "untis://setschool" + payload
        else:
            raise ValueError("QR-Payload beginnt nicht mit 'untis://'")

    parsed = urlparse(payload)
    qs = parse_qs(parsed.query)

    # parse_qs liefert Listen; wir wollen den ersten Wert
    def _first(name: str) -> str | None:
        vals = qs.get(name)
        return vals[0] if vals else None

    # url/server-Feld ist je nach Schul-Server unterschiedlich benannt
    server = _first("url") or _first("server")
    school = _first("school")
    user = _first("user")
    key = _first("key")
    school_number = _first("schoolNumber")

    if not all([server, school, user, key]):
        raise ValueError(
            "QR-Payload unvollständig – erwartet werden mindestens "
            "url, school, user, key"
        )

    return WebUntisCredentials(
        server=server,
        school=school,
        user=user,
        key=key,
        school_number=school_number,
    )


class WebUntisQRClient:
    """
    Asynchroner JSON-RPC-Client für die WebUntis-Mobile-API.

    Eine Instanz hält keine Session offen – jeder Call authentifiziert
    sich frisch via TOTP. Das ist robust gegen Session-Timeouts und
    skaliert für das HA-Polling-Intervall ausreichend.
    """

    def __init__(
        self,
        credentials: WebUntisCredentials,
        session: aiohttp.ClientSession,
    ) -> None:
        self._creds = credentials
        self._session = session

    @property
    def credentials(self) -> WebUntisCredentials:
        return self._creds

    def _endpoint(self, method: str) -> str:
        """
        Baut die JSON-RPC-URL für eine bestimmte Methode.

        Wichtig: `v=i3.2` ist Pflicht – ohne den Versions-Parameter werfen
        manche Untis-Server zwar HTTP 200, aber "Method not found".
        """
        return (
            f"https://{self._creds.server}/WebUntis/jsonrpc_intern.do"
            f"?m={method}&school={self._creds.school}&v={API_VERSION}"
        )

    def _auth_block(self) -> dict[str, Any]:
        """
        Erzeugt das `auth`-Objekt für JSON-RPC-Requests.

        WebUntis erwartet:
          - user:       Anmeldename
          - otp:        aktueller TOTP-Code (6 Ziffern, 30 s)
          - clientTime: aktuelle Client-Zeit in ms (Unix-Epoch)
        """
        totp = pyotp.TOTP(self._creds.key)
        return {
            "user": self._creds.user,
            "otp": totp.now(),
            "clientTime": int(time.time() * 1000),
        }

    async def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Führt einen einzelnen JSON-RPC-Call aus und liefert das `result`.

        Untis-Eigenheit: `params` MUSS als einelementiges Array gesendet
        werden, sonst antwortet der Server mit "Invalid method parameters".
        """
        body = {
            "id": "ha-webuntis-qr",
            "method": method,
            "params": [params],
            "jsonrpc": "2.0",
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }

        async with self._session.post(
            self._endpoint(method),
            json=body,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)

        if "error" in data and data["error"]:
            # WebUntis liefert Fehler im JSON-RPC-Format
            raise WebUntisAuthError(
                f"WebUntis-Fehler: {data['error'].get('message', data['error'])}"
            )

        return data.get("result", {})

    async def async_get_user_data(self) -> dict[str, Any]:
        """
        Ruft `getUserData2017` ab – das ist gleichzeitig der „Login"-Test.

        Liefert u. a. die personId, klassen, masterData (Fächer, Räume).
        Wird im Config-Flow zum Validieren der QR-Credentials genutzt.
        """
        params = {
            "auth": self._auth_block(),
            "deviceOs": "AND",
            "deviceOsVersion": "13",
        }
        return await self._rpc("getUserData2017", params)

    async def async_get_timetable(
        self,
        elem_id: int,
        elem_type: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """
        Holt den Stundenplan eines Untis-Elements (Schüler/Lehrer/Klasse).

        Untis-Eigenheit: `type` ist hier ein STRING wie "STUDENT" / "TEACHER" /
        "CLASS" – nicht der numerische ElementType-Code aus den älteren APIs.
        Datumsformat: YYYYMMDD als Integer.
        """
        params = {
            "auth": self._auth_block(),
            "id": elem_id,
            "type": elem_type,
            "startDate": int(start.strftime("%Y%m%d")),
            "endDate": int(end.strftime("%Y%m%d")),
            "masterDataTimestamp": 0,
        }
        result = await self._rpc("getTimetable2017", params)
        # `timetable.periods` enthält die eigentlichen Stunden
        return result.get("timetable", {}).get("periods", []) or []


class WebUntisAuthError(Exception):
    """Wird geworfen, wenn die TOTP-Authentifizierung fehlschlägt."""


def parse_period_datetime(value: int, time_value: int) -> datetime:
    """
    Konvertiert WebUntis-Datum (YYYYMMDD) + Zeit (HHMM, evtl. ohne führende 0)
    in ein naives datetime.
    """
    d = datetime.strptime(str(value), "%Y%m%d").date()
    # Zeit kommt als Integer, z.B. 815 = 08:15, 1345 = 13:45
    hh, mm = divmod(int(time_value), 100)
    return datetime.combine(d, datetime.min.time()).replace(hour=hh, minute=mm)
