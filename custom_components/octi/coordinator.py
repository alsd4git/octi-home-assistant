"""Data coordinator for Octi devices and module values."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import timedelta
from time import monotonic
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    OctiApiClient,
    OctiApiError,
    OctiAuthenticationError,
    OctiRateLimitError,
)
from .const import (
    DEFAULT_REFRESH_INTERVAL_SECONDS,
    MODULE_APPS,
    MODULE_CLIPBOARD,
    MODULE_CONNECTIVITY,
    MODULE_META,
    MODULE_POWER,
    MODULE_WIFI,
    OPTIONAL_MODULES,
    RATE_LIMIT_COOLDOWN_SECONDS,
    WS_EVENT_REFRESH_MIN_SECONDS,
    WS_RECONNECT_MAX_SECONDS,
    WS_RECONNECT_MIN_SECONDS,
)

_LOGGER = logging.getLogger(__name__)
MODULES = (MODULE_POWER, MODULE_WIFI, MODULE_CONNECTIVITY)
MODULES += (MODULE_META, MODULE_CLIPBOARD, MODULE_APPS)


class OctiCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch and cache Octi state for all entities in one config entry."""

    def __init__(
        self, hass: HomeAssistant, client: OctiApiClient, config_entry: ConfigEntry
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name="Octi",
            update_interval=timedelta(seconds=DEFAULT_REFRESH_INTERVAL_SECONDS),
        )
        self.client = client
        self._etags: dict[tuple[str, str], str] = {}
        self._websocket_task: asyncio.Task[None] | None = None
        self._rate_limit_until = 0.0
        self._last_event_refresh = 0.0
        self._pending_event_modules: set[tuple[str, str]] | None = set()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch devices and current MVP modules."""
        if self.data and monotonic() < self._rate_limit_until:
            _LOGGER.debug("Skipping Octi refresh during server-requested cooldown")
            return self.data
        try:
            devices = await self.client.async_get_devices()
            previous_modules = self.data.get("modules", {}) if self.data else {}
            device_ids = {
                device.get("id")
                for device in devices
                if isinstance(device, dict) and isinstance(device.get("id"), str)
            }
            data: dict[str, Any] = {
                "devices": devices,
                "modules": {
                    device_id: dict(modules)
                    for device_id, modules in previous_modules.items()
                    if device_id in device_ids
                },
            }
            event_modules = self._pending_event_modules
            self._pending_event_modules = set()
            self._etags = {
                (device_id, module_id): etag
                for (device_id, module_id), etag in self._etags.items()
                if device_id in device_ids
            }
            for device in devices:
                device_id = device.get("id")
                if not isinstance(device_id, str):
                    continue
                for module_id in MODULES:
                    if event_modules and (device_id, module_id) not in event_modules:
                        continue
                    result = await self.client.async_get_module(
                        device_id,
                        module_id,
                        etag=self._etags.get((device_id, module_id)),
                        optional=module_id in OPTIONAL_MODULES,
                    )
                    if result is None:
                        self._etags.pop((device_id, module_id), None)
                        data["modules"].setdefault(device_id, {}).pop(module_id, None)
                        continue
                    self._etags[(device_id, module_id)] = result.etag or self._etags.get(
                        (device_id, module_id), ""
                    )
                    if not result.not_modified:
                        data["modules"].setdefault(device_id, {})[module_id] = result.value
            self._rate_limit_until = 0.0
            return data
        except OctiAuthenticationError as err:
            raise ConfigEntryAuthFailed("Octi credentials were rejected") from err
        except OctiRateLimitError as err:
            cooldown = err.retry_after or RATE_LIMIT_COOLDOWN_SECONDS
            self._rate_limit_until = monotonic() + cooldown
            return self._keep_last_data_or_raise(err)
        except OctiApiError as err:
            return self._keep_last_data_or_raise(err)

    def _keep_last_data_or_raise(self, error: OctiApiError) -> dict[str, Any]:
        """Keep entities usable during a temporary server or network failure."""
        if self.data:
            _LOGGER.warning("Octi refresh failed; keeping the last valid data: %s", error)
            return self.data
        raise UpdateFailed("Unable to update Octi") from error

    async def async_start(self) -> None:
        """Start the event listener after the first successful refresh."""
        self._websocket_task = self.hass.async_create_background_task(
            self._async_event_loop(), name="octi-websocket"
        )

    async def async_stop(self) -> None:
        """Stop background event listening and await task cancellation."""
        task = self._websocket_task
        self._websocket_task = None
        if task is None:
            return
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    async def _async_event_loop(self) -> None:
        delay = WS_RECONNECT_MIN_SECONDS
        while True:
            try:
                async for event in self.client.async_events():
                    if _has_module_change(event):
                        await self._async_request_event_refresh(event)
                delay = WS_RECONNECT_MIN_SECONDS
            except asyncio.CancelledError:
                raise
            except OctiApiError:
                _LOGGER.warning("Octi WebSocket disconnected; retrying")
            except Exception:
                _LOGGER.exception("Unexpected Octi WebSocket failure")
            await asyncio.sleep(delay)
            delay = min(delay * 2, WS_RECONNECT_MAX_SECONDS)

    async def _async_request_event_refresh(self, event: dict[str, Any]) -> None:
        """Coalesce event bursts so one WebSocket burst cannot cause request floods."""
        event_modules = _event_module_targets(event)
        if event_modules is None:
            self._pending_event_modules = None
        elif self._pending_event_modules is not None:
            self._pending_event_modules.update(event_modules)
        now = monotonic()
        if now - self._last_event_refresh < WS_EVENT_REFRESH_MIN_SECONDS:
            return
        self._last_event_refresh = now
        await self.async_request_refresh()


def _has_module_change(event: dict[str, Any]) -> bool:
    events = event.get("events")
    return isinstance(events, list) and any(
        isinstance(item, dict) and item.get("type") == "module_changed" for item in events
    )


def _event_module_targets(event: dict[str, Any]) -> set[tuple[str, str]] | None:
    """Extract precise module targets, or return None when a full refresh is safer."""
    events = event.get("events")
    if not isinstance(events, list):
        return None
    changes = [
        item for item in events if isinstance(item, dict) and item.get("type") == "module_changed"
    ]
    targets: set[tuple[str, str]] = set()
    for item in changes:
        device_id = item.get("deviceId")
        module_id = item.get("moduleId")
        if not isinstance(device_id, str) or not isinstance(module_id, str):
            return None
        targets.add((device_id, module_id))
    return targets
