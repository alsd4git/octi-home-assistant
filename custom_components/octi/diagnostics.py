"""Diagnostics support for Octi config entries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from . import OctiConfigEntry
from .const import (
    CONF_ACCOUNT_ID,
    CONF_DEVICE_ID,
    CONF_DEVICE_PASSWORD,
    CONF_KEYSET,
    MODULE_APPS,
    MODULE_CLIPBOARD,
)

_REDACT_KEYS = {
    CONF_ACCOUNT_ID,
    CONF_DEVICE_ID,
    CONF_DEVICE_PASSWORD,
    CONF_KEYSET,
    "id",
    "deviceId",
    "sourceDeviceId",
}
_SENSITIVE_MODULES = {MODULE_APPS, MODULE_CLIPBOARD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: OctiConfigEntry
) -> dict[str, Any]:
    """Return safe diagnostics without decrypted module contents or credentials."""
    del hass
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data
    return {
        "config_entry": async_redact_data(dict(entry.data), _REDACT_KEYS),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": type(coordinator.last_exception).__name__
            if coordinator.last_exception
            else None,
        },
        "devices": async_redact_data(data.get("devices", []), _REDACT_KEYS),
        "modules": _module_summary(data.get("modules", {})),
    }


def _module_summary(modules: Any) -> list[dict[str, Any]]:
    """Summarize module availability and shape without returning payload values."""
    if not isinstance(modules, Mapping):
        return []

    summary: list[dict[str, Any]] = []
    for device_id, device_modules in modules.items():
        if not isinstance(device_id, str) or not isinstance(device_modules, Mapping):
            continue
        device_summary: dict[str, dict[str, Any]] = {}
        for module_id, value in device_modules.items():
            if not isinstance(module_id, str):
                continue
            item: dict[str, Any] = {
                "available": value is not None,
                "sensitive": module_id in _SENSITIVE_MODULES,
            }
            if isinstance(value, Mapping):
                item["fields"] = sorted(str(field) for field in value)
            else:
                item["type"] = type(value).__name__
            device_summary[module_id] = item
        summary.append({"device_id": device_id, "modules": device_summary})
    return async_redact_data(summary, _REDACT_KEYS)
