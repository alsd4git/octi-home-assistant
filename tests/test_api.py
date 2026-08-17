from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.octi.api import (
    OctiApiClient,
    OctiAuthenticationError,
)


class _Response:
    def __init__(self, status: int, *, headers: dict[str, str] | None = None) -> None:
        self.status = status
        self.headers = headers or {}

    async def read(self) -> bytes:
        return b""

    async def json(self) -> dict[str, object]:
        return {}

    def release(self) -> None:
        pass


def _client(response: _Response) -> OctiApiClient:
    session = AsyncMock()
    session.request.return_value = response
    return OctiApiClient(
        session=session,
        server="https://octi.example",
        account_id="account",
        device_password="password",
        device_id="device",
        keyset=b"keyset",
        keyset_type="AES256_GCM_SIV",
    )


@pytest.mark.asyncio
async def test_module_204_clears_the_cached_value() -> None:
    assert await _client(_Response(204)).async_get_module("target", "module", optional=True) is None


@pytest.mark.asyncio
async def test_module_304_preserves_the_cached_value() -> None:
    result = await _client(_Response(304, headers={"ETag": '"v2"'})).async_get_module(
        "target", "module", etag='"v1"'
    )

    assert result is not None
    assert result.not_modified is True
    assert result.etag == '"v2"'


@pytest.mark.asyncio
async def test_api_authentication_error_is_typed() -> None:
    with pytest.raises(OctiAuthenticationError):
        await _client(_Response(401)).async_get_devices()


@pytest.mark.asyncio
async def test_api_disables_http_redirects() -> None:
    session = AsyncMock()
    session.request.return_value = _Response(204)
    client = OctiApiClient(
        session=session,
        server="https://octi.example",
        account_id="account",
        device_password="password",
        device_id="device",
        keyset=b"keyset",
        keyset_type="AES256_GCM_SIV",
    )

    await client.async_get_module("target", "module", optional=True)

    assert session.request.call_args.kwargs["allow_redirects"] is False
