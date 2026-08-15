"""Pure helpers for mapping Octi payloads to Home Assistant values."""

from __future__ import annotations

import base64
from typing import Any

from .const import DOMAIN, MANUFACTURER


def build_device_info(
    device_id: str, device: dict[str, Any], metadata: dict[str, Any]
) -> dict[str, Any]:
    """Build Home Assistant device metadata without requiring a HA runtime."""
    name = device.get("label") or metadata.get("deviceLabel") or metadata.get("deviceName")
    if not isinstance(name, str) or not name:
        name = device_id[:8]

    info: dict[str, Any] = {
        "identifiers": {(DOMAIN, device_id)},
        "name": name,
        "manufacturer": metadata.get("deviceManufacturer") or MANUFACTURER,
    }
    model = metadata.get("deviceName")
    if not isinstance(model, str) or not model:
        model = (
            "Home Assistant" if device.get("platform") == "home_assistant" else device.get("label")
        )
    if isinstance(model, str) and model:
        info["model"] = model

    android_version = metadata.get("androidVersionName")
    os_type = metadata.get("osType")
    os_version = metadata.get("osVersionName")
    if isinstance(android_version, str) and android_version:
        info["sw_version"] = f"Android {android_version}"
    elif isinstance(os_version, str) and os_version:
        info["sw_version"] = f"{os_type} {os_version}" if os_type else os_version
    elif isinstance(device.get("version"), str) and device["version"]:
        info["sw_version"] = device["version"]
    return info


def clipboard_value(payload: dict[str, Any]) -> str | None:
    """Decode a clipboard payload, returning None for unsupported/malformed data."""
    if payload.get("type") == "EMPTY":
        return "Empty"
    if payload.get("type") != "SIMPLE_TEXT":
        return None
    encoded = payload.get("data")
    if not isinstance(encoded, str):
        return None
    try:
        return base64.b64decode(encoded, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def clipboard_attributes(payload: dict[str, Any]) -> dict[str, Any]:
    """Return safe clipboard metadata without duplicating its contents."""
    encoded = payload.get("data")
    return {
        "type": payload.get("type"),
        "data_length": len(encoded) if isinstance(encoded, str) else 0,
    }


def installed_packages(payload: dict[str, Any]) -> list[Any]:
    """Return the optional app inventory, or an empty list when absent."""
    packages = payload.get("installedPackages")
    return packages if isinstance(packages, list) else []
