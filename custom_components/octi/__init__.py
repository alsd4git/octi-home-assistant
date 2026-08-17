"""Octi Home Assistant integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .api import OctiApiClient, OctiApiError, OctiAuthenticationError
from .coordinator import OctiCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass(slots=True)
class OctiRuntimeData:
    """Runtime objects owned by one config entry."""

    client: OctiApiClient
    coordinator: OctiCoordinator


type OctiConfigEntry = ConfigEntry[OctiRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: OctiConfigEntry) -> bool:
    """Set up Octi from a config entry."""
    client = OctiApiClient.from_config_entry(hass, entry)
    coordinator = OctiCoordinator(hass, client, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        await client.async_close()
        raise
    except OctiAuthenticationError as err:
        await client.async_close()
        raise ConfigEntryAuthFailed("Octi credentials were rejected") from err
    except OctiApiError as err:
        await client.async_close()
        raise ConfigEntryNotReady("Octi is not reachable") from err
    except ConfigEntryNotReady:
        await client.async_close()
        raise
    except Exception:
        await client.async_close()
        raise

    entry.runtime_data = OctiRuntimeData(client=client, coordinator=coordinator)
    try:
        await coordinator.async_start()
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        await coordinator.async_stop()
        await client.async_close()
        entry.runtime_data = None
        raise
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OctiConfigEntry) -> bool:
    """Unload an Octi config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.coordinator.async_stop()
        await entry.runtime_data.client.async_close()
    return unload_ok
