from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.octi.button import OctiSyncButton
from custom_components.octi.const import DOMAIN


@pytest.mark.asyncio
async def test_sync_button_requests_coordinator_refresh(hass) -> None:
    coordinator = AsyncMock()
    entry = MockConfigEntry(domain=DOMAIN)
    button = OctiSyncButton(coordinator, entry.entry_id)

    await button.async_press()

    coordinator.async_request_refresh.assert_awaited_once()
