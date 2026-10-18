from __future__ import annotations

import json
import tomllib
from pathlib import Path

from custom_components.octi.const import OCTI_VERSION
from custom_components.octi.meta import build_self_meta_info


def test_build_self_meta_info_uses_upstream_wire_shape() -> None:
    assert build_self_meta_info("device-1", "2026.8.2") == {
        "deviceLabel": "Home Assistant",
        "deviceId": {"id": "device-1"},
        "octiVersionName": OCTI_VERSION,
        "octiGitSha": "community",
        "deviceManufacturer": "Home Assistant",
        "deviceName": "Home Assistant",
        "deviceType": "SERVER",
        "osType": "home_assistant",
        "osVersionName": "2026.8.2",
    }


def test_client_version_matches_integration_and_project_versions() -> None:
    root = Path(__file__).parents[1]
    manifest = json.loads((root / "custom_components/octi/manifest.json").read_text())
    project = tomllib.loads((root / "pyproject.toml").read_text())

    assert OCTI_VERSION == manifest["version"] == project["project"]["version"]
