from __future__ import annotations

import base64
import gzip
import json

import pytest

from custom_components.octi.linking import LinkingPayloadError, decode_linking_payload


def _payload(data: dict) -> str:
    raw = gzip.compress(json.dumps(data).encode())
    return base64.b64encode(raw).decode()


def test_decode_linking_payload() -> None:
    result = decode_linking_payload(
        _payload(
            {
                "serverAddress": "https://octi.example/",
                "shareCode": {"code": "ABC123"},
                "encryptionKeySet": {
                    "type": "AES256_GCM_SIV",
                    "key": base64.b64encode(b"key").decode(),
                },
            }
        )
    )

    assert result.server == "https://octi.example"
    assert result.share_code == "ABC123"
    assert result.keyset_type == "AES256_GCM_SIV"
    assert result.keyset == b"key"


def test_decode_structured_server_address() -> None:
    result = decode_linking_payload(
        _payload(
            {
                "serverAddress": {
                    "domain": "octi.example",
                    "protocol": "https",
                    "port": 443,
                },
                "shareCode": {"code": "ABC123"},
                "encryptionKeySet": {"type": "AES256_GCM_SIV", "key": "a2V5"},
            }
        )
    )

    assert result.server == "https://octi.example:443"


@pytest.mark.parametrize(
    "data",
    [
        {"serverAddress": "ftp://octi.example"},
        {"serverAddress": "https://octi.example", "shareCode": {"code": "x"}},
        {
            "serverAddress": "https://octi.example",
            "shareCode": {"code": "x"},
            "encryptionKeySet": {"type": "UNKNOWN", "key": "eA=="},
        },
    ],
)
def test_decode_rejects_invalid_payload(data: dict) -> None:
    with pytest.raises(LinkingPayloadError):
        decode_linking_payload(_payload(data))


def test_decode_rejects_plain_text() -> None:
    with pytest.raises(LinkingPayloadError):
        decode_linking_payload("not-a-payload")


def test_decode_rejects_gzip_payload_that_expands_too_far() -> None:
    with pytest.raises(LinkingPayloadError, match="too large"):
        decode_linking_payload(
            base64.b64encode(gzip.compress(b"x" * (1 * 1024 * 1024 + 1))).decode()
        )
