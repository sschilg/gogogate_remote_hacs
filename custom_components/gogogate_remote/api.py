"""GoGoGate2 API client with AES/CBC encryption."""

from __future__ import annotations

import base64
import json
import logging
import uuid
from typing import Any

_LOGGER = logging.getLogger(__name__)

SHARED_SECRET = "0e3b7%i1X9@54cAf"


def _pad_pkcs5(data: str) -> str:
    block_size = 16  # AES.block_size
    return data + (block_size - len(data) % block_size) * chr(
        block_size - len(data) % block_size
    )


def _unpad_pkcs5(data: bytes) -> bytes:
    return data[: -data[-1]]


def _encrypt(content: str) -> str:
    from Crypto.Cipher import AES

    key_bytes = SHARED_SECRET.encode("utf-8")
    iv_bytes = _pad_pkcs5(uuid.uuid4().hex).encode("utf-8")[: AES.block_size]
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
    encrypted = cipher.encrypt(_pad_pkcs5(content).encode("utf-8"))
    return (iv_bytes + base64.b64encode(encrypted)).decode("utf-8")


def _decrypt(content: str) -> str:
    from Crypto.Cipher import AES

    key_bytes = SHARED_SECRET.encode("utf-8")
    iv = content.encode("utf-8")[: AES.block_size]
    encrypted = base64.b64decode(content[AES.block_size :])
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    return _unpad_pkcs5(cipher.decrypt(encrypted)).decode("utf-8")


class GogoGate2API:
    """API client for GoGoGate2 devices via cloud relay."""

    def __init__(self, host: str, username: str, password: str, timeout: int = 15):
        self._host = host.rstrip("/")
        if not self._host.startswith("http"):
            self._host = f"https://{self._host}"
        self._username = username
        self._password = password
        self._api_url = f"{self._host}/api.php"
        self._timeout = timeout

    def _get_session(self):
        import requests
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        session = requests.Session()
        session.verify = False
        return session

    def _api_call(self, option: str, arg1: str = "", arg2: str = "") -> str:
        """Send an encrypted API request and return decrypted XML response."""
        payload = json.dumps(
            [self._username, self._password, option, arg1, arg2]
        )
        encrypted = _encrypt(payload)

        session = self._get_session()
        resp = session.get(
            self._api_url,
            params={"data": encrypted},
            timeout=self._timeout,
        )

        if resp.status_code != 200:
            raise ConnectionError(
                f"API returned HTTP {resp.status_code}: {resp.text[:200]}"
            )

        raw = resp.text.strip()
        try:
            return _decrypt(raw)
        except (ValueError, IndexError):
            # Unencrypted error response
            return raw

    def get_info(self) -> dict[str, Any]:
        """Fetch device info. Returns parsed dict with door statuses."""
        xml = self._api_call("info")
        return self._parse_info(xml)

    def get_door_status(self, door_id: int = 1) -> str:
        """Return the status of a door: opened/closed/undefined."""
        info = self.get_info()
        door = info.get(f"door{door_id}", {})
        return door.get("status", "undefined")

    def get_door_name(self, door_id: int = 1) -> str:
        """Return the name of a door."""
        info = self.get_info()
        door = info.get(f"door{door_id}", {})
        return door.get("name", "")

    def activate(self, door_id: int = 1) -> bool:
        """Send activate (open/close/toggle) command. Returns True if result=ok."""
        info = self.get_info()
        apicode = info.get("apicode", "")

        resp = self._api_call("activate", str(door_id), apicode)
        result_start = resp.find("<result>")
        result_end = resp.find("</result>")
        if result_start == -1:
            raise ConnectionError(f"Unexpected response: {resp[:200]}")
        return resp[result_start + 8 : result_end].strip().lower() == "ok"

    @staticmethod
    def _parse_info(xml: str) -> dict[str, Any]:
        """Parse the XML info response into a dict."""
        result: dict[str, Any] = {
            "user": _xml_tag(xml, "user"),
            "name": _xml_tag(xml, "gogogatename"),
            "model": _xml_tag(xml, "model"),
            "firmware": _xml_tag(xml, "firmwareversion"),
            "apiversion": _xml_tag(xml, "apiversion"),
            "apicode": _xml_tag(xml, "apicode"),
        }

        for door_id in [1, 2, 3]:
            tag = f"door{door_id}"
            start = xml.find(f"<{tag}>")
            if start == -1:
                continue
            end = xml.find(f"</{tag}>")
            block = xml[start:end]
            door = {
                "door_id": door_id,
                "name": _xml_inner(block, "name"),
                "status": _xml_inner(block, "status"),
                "mode": _xml_inner(block, "mode"),
                "sensor": _xml_inner(block, "sensor") == "yes",
                "camera": _xml_inner(block, "camera") == "yes",
                "permission": _xml_inner(block, "permission") == "yes",
                "temperature": _xml_float(block, "temperature"),
                "voltage": _xml_int(block, "voltage"),
            }
            result[f"door{door_id}"] = door

        return result


def _xml_tag(xml: str, tag: str) -> str:
    """Extract a top-level XML tag value."""
    start = xml.find(f"<{tag}>")
    if start == -1:
        return ""
    end = xml.find(f"</{tag}>")
    if end == -1:
        return ""
    return xml[start + len(tag) + 2 : end].strip()


def _xml_inner(block: str, tag: str) -> str:
    """Extract an inner XML tag value."""
    start = block.find(f"<{tag}>")
    if start == -1:
        return ""
    end = block.find(f"</{tag}>")
    if end == -1:
        return ""
    return block[start + len(tag) + 2 : end].strip()


def _xml_float(block: str, tag: str) -> float | None:
    val = _xml_inner(block, tag)
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _xml_int(block: str, tag: str) -> int | None:
    val = _xml_inner(block, tag)
    try:
        return int(val)
    except (ValueError, TypeError):
        return None
