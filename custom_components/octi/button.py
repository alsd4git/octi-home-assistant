"""Buttons exposed by Octi."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OctiConfigEntry
from .coordinator import OctiCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OctiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the manual synchronization button."""
    del hass
    async_add_entities([OctiSyncButton(entry.runtime_data.coordinator, entry.entry_id)])


class OctiSyncButton(CoordinatorEntity[OctiCoordinator], ButtonEntity):
    """Request an immediate coordinator refresh."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_icon = "mdi:sync"
    _attr_name = "Sync now"

    def __init__(self, coordinator: OctiCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_sync"

    async def async_press(self) -> None:
        """Refresh all devices and modules immediately."""
        await self.coordinator.async_request_refresh()
