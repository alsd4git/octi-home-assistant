"""Async HTTP and WebSocket client for Octi."""

from __future__ import annotations

import base64
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from aiohttp import ClientError, ClientResponse, ClientSession, WSMsgType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCOUNT_ID,
    CONF_DEVICE_ID,
    CONF_DEVICE_PASSWORD,
    CONF_KEYSET,
    CONF_KEYSET_TYPE,
    CONF_SERVER,
    OCTI_LABEL,
    OCTI_PLATFORM,
    OCTI_VERSION,
)
from .crypto import OctiCryptoError, decrypt_module_payload

_CAPABILITIES = json.dumps(
    [
        "encryption:AES256_GCM_SIV",
        "encryption:AES256_SIV",
        "encryption:_reported",
    ],
    separators=(",", ":"),
)


class OctiApiError(RuntimeError):
    """An Octi transport or protocol error."""


class OctiAuthenticationError(OctiApiError):
    """The Octi credentials were rejected."""


@dataclass(frozen=True, slots=True)
class OctiModuleValue:
    """A decrypted module value and its server metadata."""

    value: Any
    etag: str | None
    modified_at: str | None
    not_modified: bool = False


class OctiApiClient:
    """Small client containing all Octi wire details."""

    def __init__(
        self,
        *,
        session: ClientSession,
        server: str,
        account_id: str,
        device_password: str,
        device_id: str,
        keyset: bytes,
        keyset_type: str,
    ) -> None:
        self._session = session
        self.server = server.rstrip("/")
        self.account_id = account_id
        self.device_password = device_password
        self.device_id = device_id
        self.keyset = keyset
        self.keyset_type = keyset_type

    @classmethod
    def from_config_entry(cls, hass: HomeAssistant, entry: ConfigEntry) -> OctiApiClient:
        """Build a client from persisted config-entry data."""
        data = entry.data
        return cls(
            session=async_get_clientsession(hass),
            server=data[CONF_SERVER],
            account_id=data[CONF_ACCOUNT_ID],
            device_password=data[CONF_DEVICE_PASSWORD],
            device_id=data[CONF_DEVICE_ID],
            keyset=base64.b64decode(data[CONF_KEYSET]),
            keyset_type=data[CONF_KEYSET_TYPE],
        )

    def _headers(self, *, include_auth: bool = True) -> dict[str, str]:
        headers = {
            "X-Device-ID": self.device_id,
            "Octi-Device-Label": OCTI_LABEL,
            "Octi-Device-Platform": OCTI_PLATFORM,
            "Octi-Device-Version": OCTI_VERSION,
            "Octi-Device-Capabilities": _CAPABILITIES,
        }
        if include_auth:
            credentials = f"{self.account_id}:{self.device_password}".encode()
            headers["Authorization"] = f"Basic {base64.b64encode(credentials).decode()}"
        return headers

    async def async_join_account(self, share_code: str) -> dict[str, Any]:
        """Join an account using a share code and return the credential response."""
        url = f"{self.server}/v1/account?{urlencode({'share': share_code})}"
        response = await self._request("POST", url, headers=self._headers(include_auth=False))
        return await _json_response(response)

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Fetch the linked device list."""
        response = await self._request("GET", f"{self.server}/v1/devices")
        payload = await _json_response(response)
        if not isinstance(payload, dict) or not isinstance(payload.get("devices"), list):
            raise OctiApiError("Octi returned an invalid device list")
        return payload["devices"]

    async def async_get_module(
        self,
        device_id: str,
        module_id: str,
        *,
        etag: str | None = None,
        optional: bool = False,
    ) -> OctiModuleValue | None:
        """Fetch and decrypt one module; None means no current value/not modified."""
        headers = self._headers()
        if etag:
            headers["If-None-Match"] = etag
        url = f"{self.server}/v1/module/{module_id}?{urlencode({'device-id': device_id})}"
        response = await self._request("GET", url, headers=headers, allow_missing=optional)
        if response is None:
            return None
        if response.status == 204:
            response.release()
            return None
        if response.status == 304:
            etag = response.headers.get("ETag") or etag
            modified_at = response.headers.get("X-Modified-At")
            response.release()
            return OctiModuleValue(None, etag, modified_at, True)
        body = await response.read()
        try:
            value = decrypt_module_payload(
                body,
                keyset=self.keyset,
                keyset_type=self.keyset_type,
                device_id=device_id,
                module_id=module_id,
            )
        except OctiCryptoError as err:
            raise OctiApiError("Octi returned an invalid module payload") from err
        return OctiModuleValue(
            value,
            response.headers.get("ETag"),
            response.headers.get("X-Modified-At"),
        )

    async def async_events(self) -> AsyncIterator[dict[str, Any]]:
        """Yield authenticated WebSocket event envelopes until disconnected."""
        ws_url = self.server.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
        async with self._session.ws_connect(
            f"{ws_url}/v1/ws", headers=self._headers()
        ) as websocket:
            async for message in websocket:
                if message.type == WSMsgType.TEXT:
                    try:
                        payload = json.loads(message.data)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(payload, dict):
                        yield payload
                elif message.type in {WSMsgType.ERROR, WSMsgType.CLOSED, WSMsgType.CLOSE}:
                    break

    async def async_close(self) -> None:
        """Release resources owned by the client when a private session is used."""
        # Home Assistant owns the shared session; this method is intentionally a no-op.

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        auth: bool = True,
        allow_missing: bool = False,
    ) -> ClientResponse | None:
        request_headers = headers or (self._headers() if auth else {})
        try:
            response = await self._session.request(
                method,
                url,
                headers=request_headers,
                timeout=20,
                allow_redirects=False,
            )
        except (TimeoutError, ClientError) as err:
            raise OctiApiError("Octi request failed") from err
        if response.status in {401, 403}:
            response.release()
            raise OctiAuthenticationError("Octi credentials were rejected")
        if response.status == 404 and allow_missing:
            response.release()
            return None
        if response.status >= 400:
            status = response.status
            response.release()
            raise OctiApiError(f"Octi returned HTTP {status}")
        return response


async def _json_response(response: ClientResponse) -> dict[str, Any] | list[Any]:
    try:
        payload = await response.json()
    except (ClientError, json.JSONDecodeError) as err:
        raise OctiApiError("Octi returned invalid JSON") from err
    if not isinstance(payload, (dict, list)):
        raise OctiApiError("Octi returned an invalid JSON response")
    return payload
