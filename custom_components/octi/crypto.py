"""Octi payload decryption using the Home Assistant cryptography dependency."""

from __future__ import annotations

import gzip
import json
from typing import Any

from cryptography.exceptions import InvalidTag, UnsupportedAlgorithm
from cryptography.hazmat.primitives.ciphers.aead import AESGCMSIV, AESSIV

from .const import KEYSET_GCM_SIV, KEYSET_SIV


class OctiCryptoError(ValueError):
    """The payload cannot be decrypted or decoded."""


def decrypt_module_payload(
    ciphertext: bytes,
    *,
    keyset: bytes,
    keyset_type: str,
    device_id: str,
    module_id: str,
) -> Any:
    """Decrypt, gunzip and decode one Octi module payload."""
    if not ciphertext:
        raise OctiCryptoError("The encrypted payload is empty")
    try:
        aad = f"{device_id}:{module_id}".encode()
        plaintext = _decrypt_payload(
            ciphertext,
            keyset=keyset,
            keyset_type=keyset_type,
            aad=aad,
        )
        return json.loads(gzip.decompress(plaintext))
    except (
        gzip.BadGzipFile,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        InvalidTag,
        UnsupportedAlgorithm,
        ValueError,
    ) as err:
        raise OctiCryptoError("The Octi payload could not be decrypted") from err


def _decrypt_payload(
    ciphertext: bytes,
    *,
    keyset: bytes,
    keyset_type: str,
    aad: bytes,
) -> bytes:
    """Decrypt Tink wire bytes with the equivalent standard crypto primitive."""
    key_id, raw_key = _primary_key(keyset, keyset_type)
    if len(ciphertext) < 5 or ciphertext[0] != 1:
        raise OctiCryptoError("The Octi ciphertext has an invalid Tink prefix")
    if int.from_bytes(ciphertext[1:5], "big") != key_id:
        raise OctiCryptoError("The Octi ciphertext uses a different key")

    if keyset_type == KEYSET_GCM_SIV:
        if len(ciphertext) < 5 + 12 + 16:
            raise OctiCryptoError("The Octi GCM-SIV ciphertext is too short")
        return AESGCMSIV(raw_key).decrypt(ciphertext[5:17], ciphertext[17:], aad)
    if keyset_type == KEYSET_SIV:
        return AESSIV(raw_key).decrypt(ciphertext[5:], [b""])
    raise OctiCryptoError("The Octi encryption mode is not supported")


def _primary_key(keyset: bytes, keyset_type: str) -> tuple[int, bytes]:
    """Extract the enabled primary raw AES key from a binary Tink keyset."""
    fields = _parse_fields(keyset)
    primary_key_id = _first_varint(fields, 1)
    if primary_key_id is None:
        raise OctiCryptoError("The Octi keyset has no primary key")

    expected_type = {
        KEYSET_GCM_SIV: b"type.googleapis.com/google.crypto.tink.AesGcmSivKey",
        KEYSET_SIV: b"type.googleapis.com/google.crypto.tink.AesSivKey",
    }.get(keyset_type)
    if expected_type is None:
        raise OctiCryptoError("The Octi encryption mode is not supported")

    for encoded_key in _bytes_values(fields, 2):
        key_fields = _parse_fields(encoded_key)
        key_id = _first_varint(key_fields, 3)
        status = _first_varint(key_fields, 2)
        if key_id != primary_key_id or status != 1:
            continue
        key_data = _first_bytes(key_fields, 1)
        if key_data is None:
            break
        key_data_fields = _parse_fields(key_data)
        type_url = _first_bytes(key_data_fields, 1)
        key_value_message = _first_bytes(key_data_fields, 2)
        if type_url != expected_type or key_value_message is None:
            break
        value_fields = _parse_fields(key_value_message)
        value_field = 3 if keyset_type == KEYSET_GCM_SIV else 2
        raw_key = _first_bytes(value_fields, value_field)
        if raw_key:
            return primary_key_id, raw_key
        break
    raise OctiCryptoError("The Octi keyset has no usable primary key")


def _parse_fields(data: bytes) -> dict[int, list[tuple[int, bytes | int]]]:
    """Parse the small protobuf subset used by Tink keysets."""
    fields: dict[int, list[tuple[int, bytes | int]]] = {}
    offset = 0
    while offset < len(data):
        tag, offset = _read_varint(data, offset)
        field_number, wire_type = tag >> 3, tag & 7
        if field_number == 0:
            raise OctiCryptoError("The Octi keyset contains an invalid protobuf field")
        if wire_type == 0:
            value, offset = _read_varint(data, offset)
        elif wire_type == 1:
            offset += 8
            value = data[offset - 8 : offset]
        elif wire_type == 2:
            length, offset = _read_varint(data, offset)
            end = offset + length
            if end > len(data):
                raise OctiCryptoError("The Octi keyset contains truncated protobuf data")
            value = data[offset:end]
            offset = end
        elif wire_type == 5:
            end = offset + 4
            if end > len(data):
                raise OctiCryptoError("The Octi keyset contains truncated protobuf data")
            value = data[offset:end]
            offset = end
        else:
            raise OctiCryptoError("The Octi keyset contains an unsupported protobuf field")
        fields.setdefault(field_number, []).append((wire_type, value))
    return fields


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(data) and shift < 64:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, offset
        shift += 7
    raise OctiCryptoError("The Octi keyset contains an invalid protobuf varint")


def _first_varint(fields: dict[int, list[tuple[int, bytes | int]]], number: int) -> int | None:
    for wire_type, value in fields.get(number, []):
        if wire_type == 0:
            return value if isinstance(value, int) else None
    return None


def _first_bytes(fields: dict[int, list[tuple[int, bytes | int]]], number: int) -> bytes | None:
    for wire_type, value in fields.get(number, []):
        if wire_type == 2:
            return value if isinstance(value, bytes) else None
    return None


def _bytes_values(fields: dict[int, list[tuple[int, bytes | int]]], number: int) -> list[bytes]:
    return [
        value
        for wire_type, value in fields.get(number, [])
        if wire_type == 2 and isinstance(value, bytes)
    ]
