from __future__ import annotations

import asyncio
import base64
from collections.abc import Mapping
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.octi import OctiRuntimeData
from custom_components.octi.api import OctiApiError, OctiModuleValue, OctiRateLimitError
from custom_components.octi.const import (
    CONF_ACCOUNT_ID,
    CONF_DEVICE_ID,
    CONF_DEVICE_PASSWORD,
    CONF_KEYSET,
    CONF_KEYSET_TYPE,
    CONF_SERVER,
    DOMAIN,
    MODULE_APPS,
    MODULE_CLIPBOARD,
    MODULE_POWER,
)
from custom_components.octi.coordinator import OctiCoordinator
from custom_components.octi.diagnostics import async_get_config_entry_diagnostics
from custom_components.octi.sensor import _entities_for_device
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
        self.requested_modules: list[tuple[str, str]] = []

    async def async_get_devices(self) -> list[dict[str, str]]:
        devices = self.devices[min(self.refresh, len(self.devices) - 1)]
        return devices

    async def async_get_module(
        self, device_id: str, module_id: str, **kwargs: object
    ) -> OctiModuleValue | None:
        del kwargs
        self.requested_modules.append((device_id, module_id))
        if self.refresh == 0 and device_id == "device-1" and module_id == MODULE_POWER:
            return OctiModuleValue({"status": "CHARGING"}, '"power-v1"', None)
        if self.refresh == 0 and device_id == "device-1" and module_id == MODULE_CLIPBOARD:
            return OctiModuleValue({"type": "SIMPLE_TEXT", "data": "secret"}, '"clip-v1"', None)
        if self.refresh == 1 and device_id == "device-1" and module_id == MODULE_POWER:
            return OctiModuleValue(None, '"power-v1"', None, not_modified=True)
        return None

    async def async_write_module(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    async def async_events(self):
        while True:
            await asyncio.sleep(3600)
            yield {}


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
async def test_websocket_listener_is_started_as_background_task(hass) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = OctiCoordinator(hass, _SequenceClient(), entry)
    with patch.object(coordinator, "async_publish_meta_info", new_callable=AsyncMock):
        with patch.object(
            hass,
            "async_create_background_task",
            wraps=hass.async_create_background_task,
        ) as create_background_task:
            await coordinator.async_start()

    assert [call.kwargs["name"] for call in create_background_task.call_args_list] == [
        "octi-websocket",
        "octi-meta-publish",
    ]
    await coordinator.async_stop()


@pytest.mark.asyncio
async def test_rate_limit_keeps_last_valid_snapshot_and_enters_cooldown(hass) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    client = _SequenceClient()
    client.async_get_devices = AsyncMock(side_effect=OctiRateLimitError(retry_after=600))
    coordinator = OctiCoordinator(hass, client, entry)
    coordinator.data = {"devices": [{"id": "device-1"}], "modules": {"device-1": {}}}

    snapshot = await coordinator._async_update_data()
    assert snapshot is coordinator.data
    assert coordinator._rate_limit_until > 0

    await coordinator._async_update_data()
    assert client.async_get_devices.await_count == 1


@pytest.mark.asyncio
async def test_temporary_api_error_keeps_last_valid_snapshot(hass) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    client = _SequenceClient()
    client.async_get_devices = AsyncMock(side_effect=OctiApiError("temporary failure"))
    coordinator = OctiCoordinator(hass, client, entry)
    coordinator.data = {"devices": [{"id": "device-1"}], "modules": {"device-1": {}}}

    snapshot = await coordinator._async_update_data()

    assert snapshot is coordinator.data


@pytest.mark.asyncio
async def test_meta_info_is_published_to_own_device(hass) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    client = _SequenceClient()
    client.device_id = "device-1"
    client.keyset = b"keyset"
    client.keyset_type = "AES256_GCM_SIV"
    client.async_write_module = AsyncMock()
    coordinator = OctiCoordinator(hass, client, entry)

    with patch(
        "custom_components.octi.coordinator.encrypt_module_payload",
        return_value=b"encrypted-meta",
    ) as encrypt:
        await coordinator.async_publish_meta_info()

    encrypt.assert_called_once()
    client.async_write_module.assert_awaited_once_with(
        "device-1",
        "eu.darken.octi.module.core.meta",
        b"encrypted-meta",
    )


@pytest.mark.asyncio
async def test_websocket_refresh_requests_are_coalesced(hass) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = OctiCoordinator(hass, _SequenceClient(), entry)
    coordinator.async_request_refresh = AsyncMock()
    event = {
        "events": [
            {
                "type": "module_changed",
                "deviceId": "device-1",
                "moduleId": MODULE_POWER,
            }
        ]
    }

    with patch("custom_components.octi.coordinator.monotonic", side_effect=(100.0, 110.0, 131.0)):
        await coordinator._async_request_event_refresh(event)
        await coordinator._async_request_event_refresh(event)
        await coordinator._async_request_event_refresh(event)

    assert coordinator.async_request_refresh.await_count == 2


@pytest.mark.asyncio
async def test_websocket_disconnect_triggers_full_reconciliation(hass) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = OctiCoordinator(hass, _SequenceClient(), entry)
    coordinator.async_request_refresh = AsyncMock()
    coordinator._pending_event_modules = {("device-1", MODULE_POWER)}

    await coordinator._async_reconcile_after_websocket_disconnect()

    assert coordinator._pending_event_modules is None
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_event_refresh_fetches_only_changed_modules(hass) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    client = _SequenceClient()
    coordinator = OctiCoordinator(hass, client, entry)
    coordinator.data = {"devices": [{"id": "device-1"}], "modules": {"device-1": {}}}
    coordinator._pending_event_modules = {("device-1", MODULE_POWER)}

    await coordinator._async_update_data()

    assert client.requested_modules == [("device-1", MODULE_POWER)]


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
    assert initial_ids == set()

    coordinator.async_set_updated_data(
        {
            "devices": [{"id": "device-1"}, {"id": "device-2"}],
            "modules": {
                "device-1": {MODULE_CLIPBOARD: {"type": "EMPTY", "data": ""}},
                "device-2": {MODULE_POWER: {"status": "CHARGING"}},
            },
        }
    )
    await hass.async_block_till_done()

    all_ids = {entity.unique_id for entity in added}
    assert "device-2_eu.darken.octi.module.core.power_status" in all_ids
    assert not any("battery_percent" in entity_id for entity_id in all_ids)
    assert "device-1_clipboard" in all_ids
    await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_sensor_creation_requires_observed_module_fields(hass) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = OctiCoordinator(hass, _SequenceClient(), entry)
    coordinator.data = {
        "devices": [{"id": "device-1"}],
        "modules": {
            "device-1": {
                MODULE_POWER: {
                    "battery": {"level": 42, "scale": 100},
                    "chargeIO": {"currentNow": 1_250_000},
                }
            }
        },
    }

    entities = _entities_for_device(coordinator, "device-1")
    fields = {
        getattr(entity, "_field", None)
        for entity in entities
        if getattr(entity, "_module_id", None) == MODULE_POWER
    }

    assert fields == {"battery_percent", "chargeIO.currentNow"}
    assert {entity.unique_id for entity in entities} == {
        "device-1_eu.darken.octi.module.core.power_battery_percent",
        "device-1_current_now",
        "device-1_charge_speed",
    }
    await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_sensor_availability_tracks_removed_devices_and_modules(hass) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = OctiCoordinator(hass, _SequenceClient(), entry)
    coordinator.data = {
        "devices": [{"id": "device-1"}],
        "modules": {
            "device-1": {
                MODULE_POWER: {"status": "CHARGING"},
                MODULE_CLIPBOARD: {"type": "SIMPLE_TEXT", "data": "secret"},
            }
        },
    }

    entities = _entities_for_device(coordinator, "device-1")
    power = next(
        entity
        for entity in entities
        if getattr(entity, "_module_id", None) == MODULE_POWER
        and getattr(entity, "_field", None) == "status"
    )
    clipboard = next(entity for entity in entities if entity.unique_id == "device-1_clipboard")

    assert power.available is True
    assert clipboard.available is True
    assert clipboard.entity_registry_enabled_default is False

    coordinator.async_set_updated_data(
        {"devices": [{"id": "device-1"}], "modules": {"device-1": {}}}
    )
    await hass.async_block_till_done()
    assert power.available is False
    assert clipboard.available is False

    coordinator.async_set_updated_data({"devices": [], "modules": {}})
    await hass.async_block_till_done()
    assert power.available is False
    await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_apps_sensor_exposes_only_the_count(hass) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = OctiCoordinator(hass, _SequenceClient(), entry)
    coordinator.data = {
        "devices": [{"id": "device-1"}],
        "modules": {
            "device-1": {
                MODULE_APPS: {
                    "installedPackages": [
                        {"packageName": "com.example.one"},
                        {"packageName": "com.example.two"},
                    ]
                }
            }
        },
    }

    apps = next(
        entity
        for entity in _entities_for_device(coordinator, "device-1")
        if entity.unique_id == "device-1_apps"
    )
    assert apps.native_value == 2
    assert apps.extra_state_attributes is None
    assert apps.entity_registry_enabled_default is False
    await coordinator.async_shutdown()


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
