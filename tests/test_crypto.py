from __future__ import annotations

import base64
import gzip

import pytest

from custom_components.octi.const import KEYSET_GCM_SIV, KEYSET_SIV
from custom_components.octi.crypto import (
    OctiCryptoError,
    decrypt_module_payload,
    encrypt_module_payload,
)

# Static vectors generated with the upstream Tink implementation. Keeping the
# wire-format fixtures here avoids a runtime or development dependency on Tink.
GCM_KEYSET = base64.b64decode(
    "CODa0h4SZgpbCjN0eXBlLmdvb2dsZWFwaXMuY29tL2dvb2dsZS5jcnlwdG8udGluay5BZXNHY21TaXZLZXkSIhogCLiMJY6T/9RqWfiKtnNwwgoJb7rLqBH2KUlCBpyJy78YARABGODa0h4gAQ=="
)
GCM_CIPHERTEXT = base64.b64decode(
    "AQPUrWB9OSPNmsBAfBL0n2RrgjApoz8UAlrUcTTB+gayaRBs6/rvj6ybuVb0Z7ak/KlRxm4dOXkUqQzlEPgtKjSajuPlS6FT6PHdyAAQBAkHZHisPcxmr7z1vzOh8+8/dIRq4JGUFMmk6YjuD8c="
)
SIV_KEYSET = base64.b64decode(
    "CMPz6fwBEoQBCngKMHR5cGUuZ29vZ2xlYXBpcy5jb20vZ29vZ2xlLmNyeXB0by50aW5rLkFlc1NpdktleRJCEkDr5nDHgKyi293D3P2iAwGf51L9fGo4xgwMKTVpEMQwv4IGMmuZ3GetFd1fYwj8a221sV8hyDh2Ynu19xS4hSqoGAEQARjD8+n8ASAB"
)
SIV_CIPHERTEXT = base64.b64decode(
    "AR+aecPU1Qc+saWoKM7gpcLOh+1RG4T3DHo1gf9mLQaaydoc08fXus73WJ6/iFdctsoVOEbOz3PDVJmD8/GVRaOWZ1oUq84umRfQh2QL1isJ9Mq0QMTVDQvy5Vf9IBVOK8s="
)


@pytest.mark.parametrize(
    ("keyset_type", "keyset", "ciphertext"),
    [
        (KEYSET_GCM_SIV, GCM_KEYSET, GCM_CIPHERTEXT),
        (KEYSET_SIV, SIV_KEYSET, SIV_CIPHERTEXT),
    ],
)
def test_decrypt_module_payload(keyset_type: str, keyset: bytes, ciphertext: bytes) -> None:
    device_id = "device-1"
    module_id = "eu.darken.octi.module.core.power"

    assert decrypt_module_payload(
        ciphertext,
        keyset=keyset,
        keyset_type=keyset_type,
        device_id=device_id,
        module_id=module_id,
    ) == {"status": "CHARGING", "battery": {"level": 42, "scale": 100}}


@pytest.mark.parametrize(
    ("keyset_type", "keyset"),
    [(KEYSET_GCM_SIV, GCM_KEYSET), (KEYSET_SIV, SIV_KEYSET)],
)
def test_encrypt_module_payload_round_trips(keyset_type: str, keyset: bytes) -> None:
    value = {"deviceType": "SERVER", "deviceName": "Home Assistant"}
    ciphertext = encrypt_module_payload(
        value,
        keyset=keyset,
        keyset_type=keyset_type,
        device_id="device-1",
        module_id="eu.darken.octi.module.core.meta",
    )

    assert (
        decrypt_module_payload(
            ciphertext,
            keyset=keyset,
            keyset_type=keyset_type,
            device_id="device-1",
            module_id="eu.darken.octi.module.core.meta",
        )
        == value
    )


def test_gcm_siv_rejects_wrong_associated_data() -> None:
    with pytest.raises(OctiCryptoError):
        decrypt_module_payload(
            GCM_CIPHERTEXT,
            keyset=GCM_KEYSET,
            keyset_type=KEYSET_GCM_SIV,
            device_id="device-2",
            module_id="module-1",
        )


def test_invalid_keyset_is_not_exposed() -> None:
    with pytest.raises(OctiCryptoError):
        decrypt_module_payload(
            b"ciphertext",
            keyset=base64.b64decode("eA=="),
            keyset_type=KEYSET_GCM_SIV,
            device_id="device",
            module_id="module",
        )


def test_decrypt_rejects_gzip_payload_that_expands_too_far(monkeypatch) -> None:
    monkeypatch.setattr(
        "custom_components.octi.crypto._decrypt_payload",
        lambda *args, **kwargs: gzip.compress(b"x" * (8 * 1024 * 1024 + 1)),
    )

    with pytest.raises(OctiCryptoError, match="could not be decrypted"):
        decrypt_module_payload(
            b"ciphertext",
            keyset=b"keyset",
            keyset_type=KEYSET_GCM_SIV,
            device_id="device",
            module_id="module",
        )
