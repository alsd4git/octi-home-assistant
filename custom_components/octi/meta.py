"""The small self-description published by the Home Assistant Octi client."""

from __future__ import annotations

from typing import Any

from .const import OCTI_LABEL, OCTI_VERSION

META_DEVICE_TYPE_UNKNOWN = "UNKNOWN"


def build_self_meta_info(device_id: str, home_assistant_version: str) -> dict[str, Any]:
    """Build the upstream-compatible MetaInfo payload for this integration."""
    return {
        "deviceLabel": OCTI_LABEL,
        "deviceId": {"id": device_id},
        "octiVersionName": OCTI_VERSION,
        "octiGitSha": "community",
        "deviceManufacturer": "Home Assistant",
        "deviceName": "Home Assistant",
        "deviceType": META_DEVICE_TYPE_UNKNOWN,
        "osType": "home_assistant",
        "osVersionName": home_assistant_version,
    }
