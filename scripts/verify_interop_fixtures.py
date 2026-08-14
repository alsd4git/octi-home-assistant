#!/usr/bin/env python3
"""Fetch and verify the pinned Octi interop fixtures.

The script intentionally keeps the vectors out of the repository. CI can run it
with network access, while a future offline test job can point at a cached copy.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import sys
import types
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parents[1]
LOCK = ROOT / "fixture-lock.json"

# Import the crypto module without importing Home Assistant itself. This keeps
# the verifier usable in a plain Python environment while exercising the same
# implementation shipped by the integration.
sys.path.insert(0, str(ROOT))
custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)
octi_package = types.ModuleType("custom_components.octi")
octi_package.__path__ = [str(ROOT / "custom_components" / "octi")]
sys.modules.setdefault("custom_components.octi", octi_package)

from custom_components.octi.crypto import _decrypt_payload  # noqa: E402


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=20) as response:  # noqa: S310 - URL is built from a pinned SHA
        return response.read()


def main() -> int:
    lock = json.loads(LOCK.read_text())
    source = lock["source_repository"]
    commit = lock["source_commit"]
    base = f"https://raw.githubusercontent.com/{source}/{commit}/{lock['fixture_path']}"

    manifest = _fetch(f"{base}/manifest.json")
    actual_manifest_sha = hashlib.sha256(manifest).hexdigest()
    if actual_manifest_sha != lock["manifest_sha256"]:
        raise SystemExit(f"manifest digest mismatch: {actual_manifest_sha}")

    manifest_data = json.loads(manifest)
    if manifest_data.get("schemaVersion") != lock["schema_version"]:
        raise SystemExit("unsupported interop fixture schema")

    fetched: dict[str, bytes] = {}
    for filename, expected in lock["files"].items():
        content = _fetch(f"{base}/{filename}")
        fetched[filename] = content
        actual = hashlib.sha256(content).hexdigest()
        upstream = manifest_data.get("files", {}).get(filename, {}).get("sha256")
        if actual != expected or actual != upstream:
            raise SystemExit(f"fixture digest mismatch for {filename}: {actual}")
        print(f"verified {filename} ({actual})")

    _verify_tink_vectors(fetched["tink-vectors.json"])
    return 0


def _verify_tink_vectors(content: bytes) -> None:
    """Decrypt every payload-layer vector and compare its post-gzip bytes."""
    vectors = json.loads(content)
    if vectors.get("schemaVersion") != 1:
        raise SystemExit("unsupported tink fixture schema")
    for block_name, keyset_type in (("gcmsiv", "AES256_GCM_SIV"), ("siv", "AES256_SIV")):
        block = vectors[block_name]
        keyset = base64.b64decode(block["keysetBase64"], validate=True)
        for vector in block["vectors"]:
            ciphertext = base64.b64decode(vector["ciphertextBase64"], validate=True)
            compressed = _decrypt_payload(
                ciphertext,
                keyset=keyset,
                keyset_type=keyset_type,
                aad=vector["aad"].encode(),
            )
            plaintext = gzip.decompress(compressed)
            expected = base64.b64decode(vector["plaintextBase64"], validate=True)
            if plaintext != expected:
                raise SystemExit(f"plaintext mismatch for {block_name}/{vector['name']}")
    print("verified all tink payload vectors")


if __name__ == "__main__":
    sys.exit(main())
