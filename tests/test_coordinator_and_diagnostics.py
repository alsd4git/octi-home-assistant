from __future__ import annotations

import base64
from collections.abc import Mapping

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.octi import OctiRuntimeData
from custom_components.octi.api import OctiModuleValue
from custom_components.octi.const import (
    CONF_ACCOUNT_ID,
    CONF_DEVICE_ID,
    CONF_DEVICE_PASSWORD,
    CONF_KEYSET,
    CONF_KEYSET_TYPE,
    CONF_SERVER,
    DOMAIN,
    MODULE_CLIPBOARD,
    MODULE_POWER,
)
from custom_components.octi.coordinator import OctiCoordinator
from custom_components.octi.diagnostics import async_get_config_entry_diagnostics
from custom_components.octi.sensor import async_setup_entry as async_setup_sensor_entry

ENTRY_DATA = {
    CONF_SERVER: "https://octi.example",
    CONF_ACCOUNT_ID: "account-1",
    CONF_DEVICE_PASSWORD: "password-1",
    CONF_DEVICE_ID: "ha-device-1",
    CONF_KEYSET_TYPE: "AES256_GCM_SIV",
    CONF_KEYSET: base64.b64encode(b"keyset").decode(),
}


class _SequenceClient:
    def __init__(self) -> None:
        self.devices = [
            [{"id": "device-1"}],
            [{"id": "device-1"}, {"id": "device-2"}],
            [{"id": "device-2"}],
        ]
        self.refresh = 0

    async def async_get_devices(self) -> list[dict[str, str]]:
        devices = self.devices[min(self.refresh, len(self.devices) - 1)]
        return devices

    async def async_get_module(
        self, device_id: str, module_id: str, **kwargs: object
    ) -> OctiModuleValue | None:
        del kwargs
        if self.refresh == 0 and device_id == "device-1" and module_id == MODULE_POWER:
            return OctiModuleValue({"status": "CHARGING"}, '"power-v1"', None)
        if self.refresh == 0 and device_id == "device-1" and module_id == MODULE_CLIPBOARD:
            return OctiModuleValue({"type": "SIMPLE_TEXT", "data": "secret"}, '"clip-v1"', None)
        if self.refresh == 1 and device_id == "device-1" and module_id == MODULE_POWER:
            return OctiModuleValue(None, '"power-v1"', None, not_modified=True)
        return None


def _entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)


@pytest.mark.asyncio
async def test_coordinator_clears_missing_values_and_preserves_304(hass) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    client = _SequenceClient()
    coordinator = OctiCoordinator(hass, client, entry)

    first = await coordinator._async_update_data()
    coordinator.data = first
    client.refresh = 1
    second = await coordinator._async_update_data()

    assert second["modules"]["device-1"][MODULE_POWER] == {"status": "CHARGING"}
    assert MODULE_CLIPBOARD not in second["modules"]["device-1"]
    assert ("device-1", MODULE_CLIPBOARD) not in coordinator._etags
    assert "device-2" in second["modules"]

    coordinator.data = second
    client.refresh = 2
    third = await coordinator._async_update_data()
    assert "device-1" not in third["modules"]


@pytest.mark.asyncio
async def test_sensor_setup_discovers_new_devices_and_optional_modules(hass) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    client = _SequenceClient()
    coordinator = OctiCoordinator(hass, client, entry)
    coordinator.data = {"devices": [{"id": "device-1"}], "modules": {"device-1": {}}}
    entry.runtime_data = OctiRuntimeData(client=client, coordinator=coordinator)
    added = []

    await async_setup_sensor_entry(hass, entry, added.extend)
    initial_ids = {entity.unique_id for entity in added}

    coordinator.async_set_updated_data(
        {
            "devices": [{"id": "device-1"}, {"id": "device-2"}],
            "modules": {
                "device-1": {MODULE_CLIPBOARD: {"type": "EMPTY", "data": ""}},
                "device-2": {},
            },
        }
    )
    await hass.async_block_till_done()

    all_ids = {entity.unique_id for entity in added}
    assert any("battery_percent" in entity_id for entity_id in initial_ids)
    assert any(entity_id.startswith("device-2_") for entity_id in all_ids)
    assert "device-1_clipboard" in all_ids


@pytest.mark.asyncio
async def test_diagnostics_redact_credentials_and_payload_values(hass) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    client = _SequenceClient()
    coordinator = OctiCoordinator(hass, client, entry)
    coordinator.data = {
        "devices": [{"id": "device-1", "platform": "android"}],
        "modules": {
            "device-1": {
                MODULE_CLIPBOARD: {"type": "SIMPLE_TEXT", "data": "clipboard-secret"},
                "eu.darken.octi.module.core.meta": {"deviceName": "Pixel"},
            }
        },
    }
    entry.runtime_data = OctiRuntimeData(client=client, coordinator=coordinator)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    flattened = _flatten(diagnostics)

    assert "password-1" not in flattened
    assert ENTRY_DATA[CONF_KEYSET] not in flattened
    assert "clipboard-secret" not in flattened
    assert diagnostics["modules"][0]["device_id"] == "**REDACTED**"
    assert diagnostics["modules"][0]["modules"][MODULE_CLIPBOARD]["sensitive"] is True


def _flatten(value: object) -> set[str]:
    if isinstance(value, Mapping):
        return {item for key, child in value.items() for item in {str(key), *_flatten(child)}}
    if isinstance(value, list):
        return {item for child in value for item in _flatten(child)}
    return {str(value)}
