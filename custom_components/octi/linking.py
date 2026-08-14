"""Parsing and validation for Octi linking payloads."""

from __future__ import annotations

import base64
import binascii
import gzip
import json
from dataclasses import dataclass
from urllib.parse import urlparse

from .const import SUPPORTED_KEYSET_TYPES


class LinkingPayloadError(ValueError):
    """The linking payload is malformed or unsupported."""


@dataclass(frozen=True, slots=True)
class LinkingData:
    """Validated data extracted from an Octi linking payload."""

    server: str
    share_code: str
    keyset_type: str
    keyset: bytes


def decode_linking_payload(payload: str) -> LinkingData:
    """Decode Octi's base64(gzip(JSON)) linking payload."""
    if not isinstance(payload, str) or not payload.strip():
        raise LinkingPayloadError("The linking payload is empty")

    try:
        compressed = base64.b64decode(payload.strip(), validate=True)
        decoded = gzip.decompress(compressed)
        raw = json.loads(decoded)
    except (
        binascii.Error,
        gzip.BadGzipFile,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as err:
        raise LinkingPayloadError("The linking payload is not valid Octi data") from err

    if not isinstance(raw, dict):
        raise LinkingPayloadError("The linking payload must contain a JSON object")

    server = _normalise_server(raw.get("serverAddress"))
    share_code_value = raw.get("shareCode")
    keyset_value = raw.get("encryptionKeySet")
    if server is None:
        raise LinkingPayloadError("The linking payload contains an invalid server address")
    if not isinstance(share_code_value, dict) or not isinstance(share_code_value.get("code"), str):
        raise LinkingPayloadError("The linking payload does not contain a share code")
    if not isinstance(keyset_value, dict):
        raise LinkingPayloadError("The linking payload does not contain a keyset")

    keyset_type = keyset_value.get("type")
    keyset_b64 = keyset_value.get("key")
    if keyset_type not in SUPPORTED_KEYSET_TYPES:
        raise LinkingPayloadError("This Octi encryption mode is not supported")
    if not isinstance(keyset_b64, str) or not keyset_b64:
        raise LinkingPayloadError("The linking payload contains an invalid keyset")
    try:
        keyset = base64.b64decode(keyset_b64, validate=True)
    except binascii.Error as err:
        raise LinkingPayloadError("The linking payload contains an invalid keyset") from err

    return LinkingData(
        server=server.rstrip("/"),
        share_code=share_code_value["code"],
        keyset_type=keyset_type,
        keyset=keyset,
    )


def _is_valid_server(server: str) -> bool:
    """Allow only absolute HTTP(S) endpoints."""
    parsed = urlparse(server)
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
        and parsed.username is None
        and parsed.password is None
    )


def _normalise_server(raw_server: object) -> str | None:
    """Normalise Octi's structured ServerAddress to an absolute URL."""
    if isinstance(raw_server, str):
        server = raw_server.rstrip("/")
        return server if _is_valid_server(server) else None
    if not isinstance(raw_server, dict):
        return None
    domain = raw_server.get("domain")
    protocol = raw_server.get("protocol")
    port = raw_server.get("port")
    if (
        not isinstance(domain, str)
        or not domain
        or not isinstance(protocol, str)
        or protocol not in {"http", "https"}
        or not isinstance(port, int)
        or isinstance(port, bool)
        or not 1 <= port <= 65535
    ):
        return None
    server = f"{protocol}://{domain}:{port}"
    return server if _is_valid_server(server) else None
