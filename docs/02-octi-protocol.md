# Octi protocol notes

These notes describe what the integration needs today. They are derived from the Octi web client, the Octi server and the upstream interop documentation. The upstream maintainer has said that a fuller protocol document is planned, so implementation should keep the assumptions isolated and fixture-tested.

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

The Home Assistant integration should generate one stable UUID for its linked Octi device and persist it in the config entry. It should not regenerate the identity on every restart.

## Account and device discovery

The linking flow joins an account using the share code (`POST /v1/account`). After authentication, `GET /v1/devices` returns the linked devices. The integration should treat the server response as authoritative and use stable Octi device IDs as Home Assistant identifiers.

## Module reads

The relevant read endpoint is:

```text
GET /v1/module/{moduleId}?device-id={targetDeviceId}
```

The response body is an encrypted payload. `204 No Content` means that no current value is available. `ETag` and `X-Modified-At` can be used for conditional refreshes and diagnostics.

Initial module IDs:

| Home Assistant area | Octi module ID |
| --- | --- |
| Power | `eu.darken.octi.module.core.power` |
| Wi-Fi | `eu.darken.octi.module.core.wifi` |
| Connectivity | `eu.darken.octi.module.core.connectivity` |
| Metadata | `eu.darken.octi.module.core.meta` |

The integration fetches clipboard and installed-app modules only as optional, read-only diagnostics when the server exposes them. File-transfer/blob modules remain out of scope until their payloads and Home Assistant UX have an independent design and fixture suite.

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

The integration does not need to trust event contents as state. An event should mark the affected module stale and trigger a normal authenticated GET. Reconnect with bounded exponential backoff, and retain a periodic safety refresh in case an event is missed.

## Device metadata

The linked Home Assistant client appears in Octi device lists. Send a clear label such as `Home Assistant` and a platform value that identifies this integration. The metadata module is read and exposed as diagnostic state; publishing encrypted metadata or other writes remains out of scope.

## Source references

- [Octi web API client](https://github.com/d4rken-org/octi-web/blob/main/src/protocol/octi-api.ts)
- [Octi linking data](https://github.com/d4rken-org/octi-web/blob/main/src/linking/linking-data.ts)
- [Octi issue #370 and maintainer reply](https://github.com/d4rken-org/octi/issues/370#issuecomment-5278482391)
