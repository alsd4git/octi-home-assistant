from __future__ import annotations

import base64

from custom_components.octi.payloads import (
    build_device_info,
    clipboard_attributes,
    clipboard_value,
    installed_packages,
)


def test_build_device_info_uses_metadata_and_fallbacks() -> None:
    info = build_device_info(
        "device-123456",
        {"label": "Living phone"},
        {
            "deviceManufacturer": "Acme",
            "deviceName": "Acme One",
            "androidVersionName": "15",
        },
    )

    assert info["name"] == "Living phone"
    assert info["manufacturer"] == "Acme"
    assert info["model"] == "Acme One"
    assert info["sw_version"] == "Android 15"


def test_build_device_info_does_not_require_optional_metadata() -> None:
    info = build_device_info("device-123456", {}, {})

    assert info == {
        "identifiers": {("octi", "device-123456")},
        "name": "device-1",
        "manufacturer": "Octi",
    }


def test_build_device_info_labels_home_assistant_client() -> None:
    info = build_device_info(
        "ha-device",
        {"platform": "home_assistant", "version": "0.1.0"},
        {},
    )

    assert info["model"] == "Home Assistant"
    assert info["sw_version"] == "0.1.0"


def test_clipboard_helpers_handle_empty_text_and_malformed_data() -> None:
    assert clipboard_value({"type": "EMPTY", "data": ""}) == "Empty"
    assert clipboard_value(
        {"type": "SIMPLE_TEXT", "data": base64.b64encode(b"hello").decode()}
    ) == "hello"
    assert clipboard_value({"type": "SIMPLE_TEXT", "data": "not-base64"}) is None
    assert clipboard_attributes({"type": "EMPTY", "data": ""}) == {
        "type": "EMPTY",
        "data_length": 0,
    }


def test_installed_packages_missing_is_empty() -> None:
    packages = [{"packageName": "com.example.app", "versionCode": 1}]
    assert installed_packages({"installedPackages": packages}) == packages
    assert installed_packages({}) == []
