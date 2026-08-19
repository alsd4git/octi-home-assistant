from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from custom_components.octi.api import (
    OctiApiClient,
    OctiApiError,
    OctiAuthenticationError,
    OctiRateLimitError,
)
from custom_components.octi.const import MAX_JSON_RESPONSE_BYTES, MAX_MODULE_CIPHERTEXT_BYTES


class _Content:
    def __init__(self, body: bytes) -> None:
        self.body = body

    async def iter_chunked(self, size: int):
        for offset in range(0, len(self.body), size):
            yield self.body[offset : offset + size]


class _Response:
    def __init__(
        self,
        status: int,
        *,
        headers: dict[str, str] | None = None,
        body: bytes = b"{}",
    ) -> None:
        self.status = status
        self.headers = headers or {}
        self.content = _Content(body)
        self.released = False

    async def read(self) -> bytes:
        return self.content.body

    async def json(self) -> dict[str, object]:
        return {}

    def release(self) -> None:
        self.released = True


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


def test_device_capabilities_advertise_only_the_linked_encryption_mode() -> None:
    client = _client(_Response(204))

    assert json.loads(client._headers()["Octi-Device-Capabilities"]) == [
        "encryption:AES256_GCM_SIV",
        "encryption:_reported",
    ]


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
async def test_api_rate_limit_error_preserves_retry_after() -> None:
    response = _Response(429, headers={"Retry-After": "600"})

    with pytest.raises(OctiRateLimitError) as error:
        await _client(response).async_get_devices()

    assert error.value.retry_after == 600
    assert response.released is True


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


@pytest.mark.asyncio
async def test_module_body_is_rejected_before_decryption_when_too_large() -> None:
    response = _Response(
        200,
        headers={"Content-Length": str(MAX_MODULE_CIPHERTEXT_BYTES + 1)},
    )
    with pytest.raises(OctiApiError, match="oversized"):
        await _client(response).async_get_module("target", "module")
    assert response.released is True


@pytest.mark.asyncio
async def test_module_body_stream_is_stopped_at_limit() -> None:
    response = _Response(200, body=b"x" * (MAX_MODULE_CIPHERTEXT_BYTES + 1))
    with pytest.raises(OctiApiError, match="oversized"):
        await _client(response).async_get_module("target", "module")
    assert response.released is True


@pytest.mark.asyncio
async def test_json_body_is_rejected_before_parsing_when_too_large() -> None:
    response = _Response(
        200,
        headers={"Content-Length": str(MAX_JSON_RESPONSE_BYTES + 1)},
    )
    with pytest.raises(OctiApiError, match="oversized"):
        await _client(response).async_get_devices()
    assert response.released is True
