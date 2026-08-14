"""Data coordinator for Octi devices and module values."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OctiApiClient, OctiApiError, OctiAuthenticationError
from .const import (
    DEFAULT_REFRESH_INTERVAL_SECONDS,
    MODULE_APPS,
    MODULE_CLIPBOARD,
    MODULE_CONNECTIVITY,
    MODULE_META,
    MODULE_POWER,
    MODULE_WIFI,
    OPTIONAL_MODULES,
    WS_RECONNECT_MAX_SECONDS,
    WS_RECONNECT_MIN_SECONDS,
)

_LOGGER = logging.getLogger(__name__)
MODULES = (MODULE_POWER, MODULE_WIFI, MODULE_CONNECTIVITY)
MODULES += (MODULE_META, MODULE_CLIPBOARD, MODULE_APPS)


class OctiCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch and cache Octi state for all entities in one config entry."""

    def __init__(self, hass: HomeAssistant, client: OctiApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Octi",
            update_interval=timedelta(seconds=DEFAULT_REFRESH_INTERVAL_SECONDS),
        )
        self.client = client
        self._etags: dict[tuple[str, str], str] = {}
        self._websocket_task: asyncio.Task[None] | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch devices and current MVP modules."""
        try:
            devices = await self.client.async_get_devices()
            previous_modules = self.data.get("modules", {}) if self.data else {}
            data: dict[str, Any] = {
                "devices": devices,
                "modules": {
                    device_id: dict(modules) for device_id, modules in previous_modules.items()
                },
            }
            for device in devices:
                device_id = device.get("id")
                if not isinstance(device_id, str):
                    continue
                for module_id in MODULES:
                    result = await self.client.async_get_module(
                        device_id,
                        module_id,
                        etag=self._etags.get((device_id, module_id)),
                        optional=module_id in OPTIONAL_MODULES,
                    )
                    if result is not None:
                        self._etags[(device_id, module_id)] = result.etag or self._etags.get(
                            (device_id, module_id), ""
                        )
                        data["modules"].setdefault(device_id, {})[module_id] = result.value
            return data
        except OctiAuthenticationError:
            raise
        except OctiApiError as err:
            raise UpdateFailed("Unable to update Octi") from err

    async def async_start(self) -> None:
        """Start the event listener after the first successful refresh."""
        self._websocket_task = self.hass.async_create_task(
            self._async_event_loop(), name="octi-websocket"
        )

    def async_stop(self) -> None:
        """Stop background event listening."""
        if self._websocket_task:
            self._websocket_task.cancel()

    async def _async_event_loop(self) -> None:
        delay = WS_RECONNECT_MIN_SECONDS
        while True:
            try:
                async for event in self.client.async_events():
                    if _has_module_change(event):
                        await self.async_request_refresh()
                delay = WS_RECONNECT_MIN_SECONDS
            except asyncio.CancelledError:
                raise
            except OctiApiError:
                _LOGGER.warning("Octi WebSocket disconnected; retrying")
            except Exception:
                _LOGGER.exception("Unexpected Octi WebSocket failure")
            await asyncio.sleep(delay)
            delay = min(delay * 2, WS_RECONNECT_MAX_SECONDS)


def _has_module_change(event: dict[str, Any]) -> bool:
    events = event.get("events")
    return isinstance(events, list) and any(
        isinstance(item, dict) and item.get("type") == "module_changed" for item in events
    )
