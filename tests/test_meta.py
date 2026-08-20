from __future__ import annotations

from custom_components.octi.meta import build_self_meta_info


def test_build_self_meta_info_uses_upstream_wire_shape() -> None:
    assert build_self_meta_info("device-1", "2026.8.2") == {
        "deviceLabel": "Home Assistant",
        "deviceId": {"id": "device-1"},
        "octiVersionName": "0.1.0",
        "octiGitSha": "community",
        "deviceManufacturer": "Home Assistant",
        "deviceName": "Home Assistant",
        "deviceType": "UNKNOWN",
        "osType": "home_assistant",
        "osVersionName": "2026.8.2",
    }
