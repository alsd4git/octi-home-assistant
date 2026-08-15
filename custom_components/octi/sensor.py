"""Sensors exposed by Octi."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OctiConfigEntry
from .const import (
    MODULE_APPS,
    MODULE_CLIPBOARD,
    MODULE_CONNECTIVITY,
    MODULE_META,
    MODULE_POWER,
    MODULE_WIFI,
)
from .coordinator import OctiCoordinator
from .payloads import (
    build_device_info,
    clipboard_attributes,
    clipboard_value,
    installed_packages,
)

_METADATA_FIELDS = (
    ("device_label", "Device label", "deviceLabel"),
    ("device_type", "Device type", "deviceType"),
    ("octi_version", "Octi version", "octiVersionName"),
    ("octi_git_sha", "Octi build", "octiGitSha"),
    ("device_booted_at", "Device booted", "deviceBootedAt"),
    ("android_version", "Android version", "androidVersionName"),
    ("android_api_level", "Android API level", "androidApiLevel"),
    ("android_security_patch", "Android security patch", "androidSecurityPatch"),
    ("os_type", "Operating system", "osType"),
    ("os_version", "OS version", "osVersionName"),
)

_DEVICE_FIELDS = (
    ("platform", "Platform", "platform"),
    ("client_version", "Client version", "version"),
    ("last_seen", "Last update", "lastSeen"),
    ("added_at", "Added at", "addedAt"),
    ("capabilities", "Capabilities", "capabilities"),
)

_POWER_FIELDS = (
    ("battery_health", "Battery health", "battery.health"),
    ("battery_temperature", "Battery temperature", "battery.temp"),
    ("current_now", "Current now", "chargeIO.currentNow"),
    ("current_average", "Average current", "chargeIO.currentAvg"),
    ("charge_full_at", "Estimated full", "chargeIO.fullAt"),
    ("charge_empty_at", "Estimated empty", "chargeIO.emptyAt"),
    ("charge_full_since", "Full since", "chargeIO.fullSince"),
    ("charge_speed", "Charge speed", "chargeIO.currentNow"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OctiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up diagnostic sensors and discover new Octi devices over time."""
    coordinator = entry.runtime_data.coordinator
    added_unique_ids: set[str] = set()

    @callback
    def _async_add_new_entities() -> None:
        entities = [
            entity
            for device in coordinator.data.get("devices", [])
            if isinstance(device, dict) and isinstance(device.get("id"), str)
            for entity in _entities_for_device(coordinator, device["id"])
            if entity.unique_id not in added_unique_ids
        ]
        if not entities:
            return
        added_unique_ids.update(entity.unique_id for entity in entities if entity.unique_id)
        async_add_entities(entities)

    _async_add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_entities))


def _entities_for_device(coordinator: OctiCoordinator, device_id: str) -> list[SensorEntity]:
    """Build all entities currently supported by one Octi device."""
    entities: list[SensorEntity] = [
        OctiModuleSensor(coordinator, device_id, MODULE_POWER, "battery_percent"),
        OctiModuleSensor(coordinator, device_id, MODULE_POWER, "status"),
        OctiModuleSensor(coordinator, device_id, MODULE_WIFI, "currentWifi.ssid"),
        OctiModuleSensor(coordinator, device_id, MODULE_CONNECTIVITY, "connectionType"),
    ]
    entities.extend(
        OctiModuleSensor(coordinator, device_id, MODULE_POWER, field, suffix, label)
        for suffix, label, field in _POWER_FIELDS
    )

    device = _device_record(coordinator, device_id)
    entities.extend(
        OctiDeviceMetadataSensor(coordinator, device_id, suffix, label, field)
        for suffix, label, field in _DEVICE_FIELDS
        if device.get(field) is not None
    )

    metadata = _module_data(coordinator, device_id, MODULE_META)
    entities.extend(
        OctiMetadataSensor(coordinator, device_id, suffix, label, field)
        for suffix, label, field in _METADATA_FIELDS
        if metadata.get(field) is not None
    )

    if _module_data_or_none(coordinator, device_id, MODULE_CLIPBOARD) is not None:
        entities.append(OctiClipboardSensor(coordinator, device_id))

    apps = _module_data_or_none(coordinator, device_id, MODULE_APPS)
    if apps is not None and isinstance(apps.get("installedPackages"), list):
        entities.append(OctiAppsSensor(coordinator, device_id))
    return entities


def _module_data(coordinator: OctiCoordinator, device_id: str, module_id: str) -> dict[str, Any]:
    """Return a module mapping, or an empty mapping when it is unavailable."""
    return _module_data_or_none(coordinator, device_id, module_id) or {}


def _module_data_or_none(
    coordinator: OctiCoordinator, device_id: str, module_id: str
) -> dict[str, Any] | None:
    modules = coordinator.data.get("modules", {}).get(device_id, {})
    value = modules.get(module_id) if isinstance(modules, dict) else None
    return value if isinstance(value, dict) else None


def _device_record(coordinator: OctiCoordinator, device_id: str) -> dict[str, Any]:
    for device in coordinator.data.get("devices", []):
        if isinstance(device, dict) and device.get("id") == device_id:
            return device
    return {}


def _device_info(coordinator: OctiCoordinator, device_id: str) -> dict[str, Any]:
    """Build Home Assistant device metadata from the list and meta module."""
    device = _device_record(coordinator, device_id)
    info = build_device_info(
        device_id,
        device,
        _module_data(coordinator, device_id, MODULE_META),
    )
    if device.get("platform") == "home_assistant":
        info["entry_type"] = DeviceEntryType.SERVICE
    return info


class _OctiSensor(CoordinatorEntity[OctiCoordinator], SensorEntity):
    """Base class for entities grouped under one Octi device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: OctiCoordinator, device_id: str, suffix: str, name: str
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_{suffix}"
        self._attr_name = name

    @property
    def device_info(self) -> dict[str, Any]:
        """Keep the registry metadata current when the meta module changes."""
        return _device_info(self.coordinator, self._device_id)


class OctiModuleSensor(_OctiSensor):
    """Read one scalar field from a module payload."""

    def __init__(
        self,
        coordinator: OctiCoordinator,
        device_id: str,
        module_id: str,
        field: str,
        suffix: str | None = None,
        name: str | None = None,
    ) -> None:
        super().__init__(
            coordinator,
            device_id,
            suffix or f"{module_id}_{field}",
            name or _field_label(field),
        )
        self._module_id = module_id
        self._field = field
        self._value_key = suffix or field
        if field == "battery_percent":
            self._attr_device_class = SensorDeviceClass.BATTERY
            self._attr_native_unit_of_measurement = PERCENTAGE
        elif field == "battery.temp":
            self._attr_native_unit_of_measurement = "°C"
        elif (
            field in {"chargeIO.currentNow", "chargeIO.currentAvg"}
            and self._value_key != "charge_speed"
        ):
            self._attr_native_unit_of_measurement = "mA"

    @property
    def native_value(self) -> Any:
        """Return the current field value."""
        module = _module_data(self.coordinator, self._device_id, self._module_id)
        if self._field == "battery_percent":
            battery = module.get("battery") if isinstance(module, dict) else None
            if not isinstance(battery, dict):
                return None
            level = battery.get("level")
            scale = battery.get("scale")
            if not isinstance(level, (int, float)) or not isinstance(scale, (int, float)):
                return None
            return round(level / scale * 100) if scale > 0 else None
        if not isinstance(module, dict):
            return None
        value: Any = module
        for component in self._field.split("."):
            if not isinstance(value, dict):
                return None
            value = value.get(component)
        if self._value_key == "charge_speed":
            return _charge_speed(value)
        if self._field in {"chargeIO.currentNow", "chargeIO.currentAvg"}:
            return value / 1000 if isinstance(value, (int, float)) else None
        if self._field in {"chargeIO.fullAt", "chargeIO.emptyAt", "chargeIO.fullSince"}:
            return _parse_timestamp(value)
        if self._field == "battery.health":
            return _battery_health_label(value)
        return value


class OctiDeviceMetadataSensor(_OctiSensor):
    """Expose a value from the device discovery record."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: OctiCoordinator,
        device_id: str,
        suffix: str,
        name: str,
        field: str,
    ) -> None:
        super().__init__(coordinator, device_id, f"device_{suffix}", name)
        self._field = field
        if field in {"lastSeen", "addedAt"}:
            self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> Any:
        value = _device_record(self.coordinator, self._device_id).get(self._field)
        if self._field in {"lastSeen", "addedAt"}:
            return _parse_timestamp(value)
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return value


class OctiMetadataSensor(_OctiSensor):
    """Expose one optional field from Octi's metadata module."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: OctiCoordinator,
        device_id: str,
        suffix: str,
        name: str,
        field: str,
    ) -> None:
        super().__init__(coordinator, device_id, f"meta_{suffix}", name)
        self._field = field

    @property
    def native_value(self) -> Any:
        return _module_data(self.coordinator, self._device_id, MODULE_META).get(self._field)


class OctiClipboardSensor(_OctiSensor):
    """Expose simple-text clipboard contents when the optional module is available."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:clipboard-text-outline"

    def __init__(self, coordinator: OctiCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "clipboard", "Clipboard")

    def _payload(self) -> dict[str, Any]:
        return _module_data(self.coordinator, self._device_id, MODULE_CLIPBOARD)

    @property
    def native_value(self) -> str | None:
        payload = self._payload()
        if payload.get("type") == "EMPTY":
            return "Empty"
        if payload.get("type") != "SIMPLE_TEXT":
            return None
        return clipboard_value(payload)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        payload = self._payload()
        return clipboard_attributes(payload)


class OctiAppsSensor(_OctiSensor):
    """Expose the optional installed-app inventory as a count plus attributes."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:apps"

    def __init__(self, coordinator: OctiCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "apps", "Installed apps")

    def _packages(self) -> list[Any]:
        return installed_packages(_module_data(self.coordinator, self._device_id, MODULE_APPS))

    @property
    def native_value(self) -> int:
        return len(self._packages())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"installed_packages": self._packages()}


def _field_label(field: str) -> str:
    return {
        "battery_percent": "Battery",
        "status": "Power status",
        "currentWifi.ssid": "Wi-Fi SSID",
        "connectionType": "Connection type",
    }.get(field, field.replace("_", " ").replace(".", " ").title())


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _charge_speed(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    if value > 2_500_000:
        return "FAST"
    if value > 1_000_000:
        return "NORMAL"
    return "SLOW" if value > 0 else "NORMAL"


def _battery_health_label(value: Any) -> str | None:
    return (
        {
            1: "UNKNOWN",
            2: "GOOD",
            3: "OVERHEAT",
            4: "DEAD",
            5: "OVER_VOLTAGE",
            6: "UNSPECIFIED_FAILURE",
            7: "COLD",
        }.get(value)
        if isinstance(value, int)
        else None
    )
