"""Constants for the Octi integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "octi"
NAME: Final = "Octi"
MANUFACTURER: Final = "Octi"

CONF_SERVER: Final = "server"
CONF_ACCOUNT_ID: Final = "account_id"
CONF_DEVICE_PASSWORD: Final = "device_password"
CONF_DEVICE_ID: Final = "device_id"
CONF_KEYSET_TYPE: Final = "keyset_type"
CONF_KEYSET: Final = "keyset"

KEYSET_GCM_SIV: Final = "AES256_GCM_SIV"
KEYSET_SIV: Final = "AES256_SIV"
SUPPORTED_KEYSET_TYPES: Final = frozenset({KEYSET_GCM_SIV, KEYSET_SIV})

MODULE_POWER: Final = "eu.darken.octi.module.core.power"
MODULE_WIFI: Final = "eu.darken.octi.module.core.wifi"
MODULE_CONNECTIVITY: Final = "eu.darken.octi.module.core.connectivity"
MODULE_META: Final = "eu.darken.octi.module.core.meta"
MODULE_CLIPBOARD: Final = "eu.darken.octi.module.core.clipboard"
MODULE_APPS: Final = "eu.darken.octi.module.core.apps"

OPTIONAL_MODULES: Final = frozenset({MODULE_META, MODULE_CLIPBOARD, MODULE_APPS})

OCTI_PLATFORM: Final = "home_assistant"
OCTI_VERSION: Final = "0.1.0"
OCTI_LABEL: Final = "Home Assistant"

DEFAULT_REFRESH_INTERVAL_SECONDS: Final = 300
WS_RECONNECT_MIN_SECONDS: Final = 5
WS_RECONNECT_MAX_SECONDS: Final = 300

MAX_LINKING_PAYLOAD_BASE64_CHARS: Final = 1_048_576
MAX_LINKING_PAYLOAD_COMPRESSED_BYTES: Final = 256 * 1024
MAX_LINKING_PAYLOAD_DECOMPRESSED_BYTES: Final = 1 * 1024 * 1024
MAX_MODULE_CIPHERTEXT_BYTES: Final = 4 * 1024 * 1024
MAX_MODULE_COMPRESSED_BYTES: Final = 4 * 1024 * 1024
MAX_MODULE_DECOMPRESSED_BYTES: Final = 8 * 1024 * 1024
MAX_JSON_RESPONSE_BYTES: Final = 1 * 1024 * 1024
