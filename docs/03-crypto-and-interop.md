# Cryptography and interoperability

Cryptography is the part most likely to produce a client that appears to work while silently failing to interoperate. The integration must therefore be driven by the upstream vectors before it is connected to Home Assistant entities.

## Account keyset modes

The linking payload carries the account-wide keyset mode:

- `AES256_GCM_SIV`: Tink AEAD, with associated data `deviceId:moduleId`.
- `AES256_SIV`: Tink Deterministic AEAD, used by legacy accounts; associated data is ignored.

An account uses one mode consistently. The maintainer has confirmed that newer accounts use GCM-SIV and older accounts may use SIV. The runtime uses the `cryptography` AEAD primitives and parses the small binary Tink keyset envelope locally. Tink is the wire-format/protocol name here; the integration does not install the Tink Python package.

The client must advertise only the modes it really implements in `Octi-Device-Capabilities`.

## Module payload pipeline

For the core module payloads, the current web client performs this logical pipeline:

```text
JSON module value
  -> UTF-8 bytes
  -> gzip
  -> Tink AEAD/Deterministic AEAD encryption
  -> Tink wire bytes
```

For GCM-SIV, the associated data is the UTF-8 string `{targetDeviceId}:{moduleId}`. The integration should make the target device ID and module ID explicit parameters so an accidental empty or swapped value cannot be hidden in a helper.

Streaming/blob encryption is a separate layer with different vectors and is deferred from the MVP.

## Interop fixture policy

The canonical fixtures live in `d4rken-org/octi` at:

```text
sync-core/src/test/resources/interop/
```

`tink-vectors.json` covers both account modes. `streaming-vectors.json` is retained for a later blob milestone. The upstream README requires consumers to:

1. pin a full 40-character `octi` commit SHA;
2. fetch the fixture directory at that exact SHA;
3. verify the fixture manifest and every listed SHA-256 digest;
4. reject an unknown schema version;
5. decrypt, gunzip and compare every expected plaintext.

The initial pin and observed digests, including the manifest digest, are recorded in [`fixture-lock.json`](../fixture-lock.json). [`scripts/verify_interop_fixtures.py`](../scripts/verify_interop_fixtures.py) re-checks the hashes and decrypts every payload vector; CI should run it rather than trusting this file blindly.

## Test cases to implement

- GCM-SIV vector with the exact AAD from the fixture.
- Legacy SIV vector, proving the AAD parameter does not alter the result.
- Invalid base64, malformed Tink keyset and unsupported keyset type.
- Wrong target device ID or module ID, proving GCM-SIV authentication fails.
- Valid ciphertext with invalid gzip/JSON, returning a controlled protocol error.
- `204 No Content` and ETag-not-modified paths at the API layer.

No keyset, plaintext module value or decrypted payload should be printed in test failure output unless a test deliberately uses a synthetic fixture.

## References

- [Upstream interop README](https://github.com/d4rken-org/octi/tree/main/sync-core/src/test/resources/interop)
- [Octi web payload crypto](https://github.com/d4rken-org/octi-web/tree/main/src/crypto)
