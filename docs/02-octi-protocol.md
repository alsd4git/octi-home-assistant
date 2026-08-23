# Octi protocol notes

These notes describe the Home Assistant-specific choices made on top of the [upstream Octi
protocol reference](https://github.com/d4rken-org/octi/tree/main/docs/protocol). The upstream
reference is the canonical source for the wire contract; these notes keep only the assumptions and
policies that matter to this integration.

The current upstream reference records the Android client at
`8aeacf4c7e5641716c33a6fd77c54ba73ea45fd7` and the sync server at
`7e813e2b7d198daae30bdb3cc17e5544ab9b3c22`. Re-check those revisions when changing protocol
code, because HTTP and WebSocket behavior is documented prose while the published crypto vectors
are machine-checked.

## Linking payload

The web client uses a compact payload with this logical shape:

```json
{
  "serverAddress": {
    "domain": "octi.example",
    "protocol": "https",
    "port": 443
  },
  "shareCode": { "code": "..." },
  "encryptionKeySet": {
    "type": "AES256_GCM_SIV",
    "key": "<base64 Tink keyset>"
  }
}
```

On the wire the JSON is gzipped and then base64 encoded. The exact field names and keyset bytes must be treated as protocol input, not as a Home Assistant-specific format.

## HTTP authentication and identity

Authenticated requests use:

- `Authorization: Basic base64(accountId:devicePassword)`;
- `X-Device-ID` for the linked Octi device identity;
- `Octi-Device-Platform` and `Octi-Device-Version`;
- `Octi-Device-Label` for a user-visible label;
- `Octi-Device-Capabilities`, including the encryption modes actually supported by the client.

The integration identifies itself as `home_assistant`, uses the integration version as its
advertised version and sends a canonical capability set containing the linked keyset's
encryption mode plus `encryption:_reported`. It does not claim support for another mode merely
because the decoder has compatibility code for it. The integration publishes one small encrypted
self `MetaInfo` module so other clients can identify the Home Assistant participant; it does not
publish peer state or any sensitive optional module.

The Home Assistant integration should generate one stable UUID for its linked Octi device and persist it in the config entry. It should not regenerate the identity on every restart.

## Account and device discovery

The linking flow joins an account using the share code (`POST /v1/account`). After authentication, `GET /v1/devices` returns the linked devices. The integration should treat the server response as authoritative and use stable Octi device IDs as Home Assistant identifiers.

The Octi account is the sharing boundary: the protocol does not provide per-device or per-module
permissions. Every authenticated device can read peer documents, and the server does not enforce a
read-only or write-only role. This integration therefore exposes peer data read-only and writes
only its own encrypted `MetaInfo` slot.

## Module reads

The relevant read endpoint is:

```text
GET /v1/module/{moduleId}?device-id={targetDeviceId}
```

The response body is an encrypted payload. `204 No Content` means that no current value is available. `ETag` and `X-Modified-At` can be used for conditional refreshes and diagnostics.

The server uses `404` for both an unknown authenticated caller and an unknown target device. The
integration treats `404` from device discovery as an authentication failure (so Home Assistant can
offer reauthentication), while an optional module `404` only invalidates that module's cached value.

Initial module IDs:

| Home Assistant area | Octi module ID |
| --- | --- |
| Power | `eu.darken.octi.module.core.power` |
| Wi-Fi | `eu.darken.octi.module.core.wifi` |
| Connectivity | `eu.darken.octi.module.core.connectivity` |
| Metadata | `eu.darken.octi.module.core.meta` |

The integration fetches clipboard and installed-app modules only as optional, read-only diagnostics when the server exposes them. Home Assistant exposes the installed-app module as a count and does not persist the full inventory in entity attributes. File-transfer/blob modules remain out of scope until their payloads and Home Assistant UX have an independent design and fixture suite.

## WebSocket updates

The authenticated endpoint is `/v1/ws`. The server sends an event envelope like:

```json
{
  "events": [
    {
      "type": "module_changed",
      "deviceId": "target-device-uuid",
      "moduleId": "eu.darken.octi.module.core.power",
      "modifiedAt": "2026-01-01T12:00:00Z",
      "action": "updated",
      "sourceDeviceId": "actor-device-uuid"
    }
  ]
}
```

The integration does not need to trust event contents as state. An event should mark the affected
module stale and trigger a normal authenticated GET. WebSocket delivery is best effort: after every
disconnect, the integration performs a full HTTP reconciliation before reconnecting, then keeps the
periodic five-minute safety refresh in case a notification was dropped while the socket was up.

## Device metadata

The linked Home Assistant client appears in Octi device lists. Send the clear label `Home Assistant` and the free-form platform value `home_assistant`; do not substitute `web`. The integration publishes `MetaInfo.deviceType = SERVER`, the generic type for server, NAS and headless container clients. Older clients may not decode this newer type, so the compatibility caveat is documented in the README. The metadata module is read and exposed as diagnostic state; publishing the small encrypted self-description is the only write performed by this integration.

## Source references

- [Octi web API client](https://github.com/d4rken-org/octi-web/blob/main/src/protocol/octi-api.ts)
- [Octi linking data](https://github.com/d4rken-org/octi-web/blob/main/src/linking/linking-data.ts)
- [Octi protocol reference](https://github.com/d4rken-org/octi/tree/main/docs/protocol)
- [Octi issue #370 and maintainer reply](https://github.com/d4rken-org/octi/issues/370#issuecomment-5278482391)
