from __future__ import annotations

import asyncio
import base64
import gzip
import json
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.exceptions import ConfigEntryAuthFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.octi import async_setup_entry
from custom_components.octi.api import OctiAuthenticationError
from custom_components.octi.config_flow import OctiConfigFlow
from custom_components.octi.const import (
    CONF_ACCOUNT_ID,
    CONF_DEVICE_ID,
    CONF_DEVICE_PASSWORD,
    CONF_KEYSET,
    CONF_KEYSET_TYPE,
    CONF_SERVER,
    DOMAIN,
)
from custom_components.octi.coordinator import OctiCoordinator

ENTRY_DATA = {
    CONF_SERVER: "https://octi.example",
    CONF_ACCOUNT_ID: "account-1",
    CONF_DEVICE_PASSWORD: "password-1",
    CONF_DEVICE_ID: "ha-device-1",
    CONF_KEYSET_TYPE: "AES256_GCM_SIV",
    CONF_KEYSET: base64.b64encode(b"keyset").decode(),
}


class _FakeClient:
    def __init__(self, *, authentication_error: bool = False) -> None:
        self.authentication_error = authentication_error
        self.closed = False

    async def async_get_devices(self) -> list[dict[str, str]]:
        if self.authentication_error:
            raise OctiAuthenticationError("rejected")
        return [{"id": "device-1", "platform": "android", "version": "1.0"}]

    async def async_get_module(self, *args: object, **kwargs: object) -> None:
        return None

    async def async_events(self):
        while True:
            await asyncio.sleep(3600)
            yield {}

    async def async_close(self) -> None:
        self.closed = True


def _entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)


@pytest.mark.asyncio
async def test_setup_and_unload_closes_client(hass, enable_custom_integrations) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    client = _FakeClient()

    with (
        patch("custom_components.octi.OctiApiClient.from_config_entry", return_value=client),
        patch.object(OctiCoordinator, "async_start", new_callable=AsyncMock),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED

        assert await hass.config_entries.async_unload(entry.entry_id)
        assert client.closed is True


@pytest.mark.asyncio
async def test_authentication_failure_closes_client(hass) -> None:
    entry = _entry()
    client = _FakeClient(authentication_error=True)

    with (
        patch("custom_components.octi.OctiApiClient.from_config_entry", return_value=client),
        patch.object(
            OctiCoordinator,
            "async_config_entry_first_refresh",
            new_callable=AsyncMock,
            side_effect=ConfigEntryAuthFailed("rejected"),
        ),
    ):
        with pytest.raises(ConfigEntryAuthFailed):
            await async_setup_entry(hass, entry)

    assert client.closed is True


def _linking_payload() -> str:
    payload = {
        "serverAddress": "https://octi.example",
        "shareCode": {"code": "fresh-share"},
        "encryptionKeySet": {
            "type": "AES256_GCM_SIV",
            "key": base64.b64encode(b"new-keyset").decode(),
        },
    }
    return base64.b64encode(gzip.compress(json.dumps(payload).encode())).decode()


@pytest.mark.asyncio
async def test_reauth_updates_credentials_and_keeps_device_id(
    hass, enable_custom_integrations
) -> None:
    entry = _entry()
    entry.add_to_hass(hass)

    async def fake_join(flow, linking, device_id=None):
        flow._device_id = device_id
        return {"account": "account-1", "password": "password-2"}

    with patch.object(OctiConfigFlow, "_async_join", fake_join):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"linking_payload": _linking_payload()}
        )

    assert result["type"] == "abort"
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_DEVICE_ID] == "ha-device-1"
    assert entry.data[CONF_DEVICE_PASSWORD] == "password-2"
