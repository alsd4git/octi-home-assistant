# Home Assistant architecture

## Config Flow

The Config Flow should accept the complete linking payload as a paste operation. It should:

1. decode base64 and gunzip the payload;
2. validate the JSON shape and supported keyset type;
3. validate the server URL (`https` by default; `http` only when the user explicitly supplies it);
4. join the account with a generated, persisted device UUID;
5. perform one authenticated discovery request;
6. create a config entry with a stable unique ID.

Errors should be actionable: expired share code, malformed payload, unsupported encryption mode, TLS/network failure and account rejection should not collapse into one generic error.

## Stored data

Use the config entry, not YAML and not an ad-hoc file, for the account credentials and key material. The entry needs the server address, account ID, device password, Home Assistant device UUID, keyset type and keyset bytes (or the exact serialized representation needed by the crypto library). Redact these fields from diagnostics and logs. Duplicate initial setup is rejected after the join returns the account ID; the linking payload does not expose that ID, and a keyset fingerprint is not documented as a stable account identifier, so a pre-join guard would be speculative.

If Home Assistant's config-entry migration or credential helper offers a more protected storage path in the minimum supported version, use it and document the compatibility constraint.

## API client

Keep protocol code separate from entity code. A small client layer should own:

- URL construction and request timeouts;
- authentication and Octi headers;
- ETag/`X-Modified-At` handling;
- linking/discovery;
- encrypted module fetch and typed decode errors;
- WebSocket connection and event parsing.

The client should never return raw encrypted bytes to entities and should never log request headers.

## Coordinator

Use a `DataUpdateCoordinator` (or the equivalent supported by the chosen Home Assistant minimum version) as the single source of truth. The coordinator should:

- perform an initial discovery and module refresh;
- keep per-device/per-module cached values and modification times;
- mark modules stale when a WebSocket event arrives;
- debounce bursts of events;
- reconcile all devices and modules over HTTP after a WebSocket disconnect, then reconnect with bounded backoff;
- run periodic conditional refreshes as a safety net;
- expose a degraded-but-available state when the WebSocket is down but HTTP refresh succeeds.

Avoid one polling task per entity. One coordinator should serve all entities for a config entry.

## Entities

Sensors represent stable values from power, Wi-Fi and connectivity, plus the documented metadata module. Device grouping uses the Octi device ID and a deterministic Home Assistant identifier. A sensor is registered only after its module and required field have been observed; the coordinator listener adds sensors dynamically when fields appear later. Optional clipboard and installed-app modules are fetched defensively: `204` and `404` clear the cached value and leave the entity unavailable, while `304` preserves the previous value. A missing optional module never fails the config entry.

Entities include battery level, charging state, Wi-Fi SSID/signal, connectivity status, device metadata, clipboard text and the installed-app count. The power payload also exposes battery health/temperature, instantaneous and average current, charge/discharge estimates (`fullAt`, `emptyAt`, `fullSince`) and the derived charge speed. Clipboard and app entities are disabled by default and must be enabled individually because they can contain sensitive information; the full app inventory is intentionally not persisted in entity attributes. File transfer remains a future capability and is intentionally not part of this read-mostly milestone.

The integration is an Octi account hub (`integration_type: hub`). The local Home Assistant client is represented as a service entry, while linked Android, desktop and browser peers remain normal devices; assigning every peer the Home Assistant `service` entry type would misrepresent physical endpoints. The devices dashboard's `Condizione` column is the registry's disabled state, so `—` means the device is enabled, not that Octi failed to provide an online condition. The last server-observed update is exposed as the `Last update` diagnostic sensor from `lastSeen`.

When an Octi device disappears, its cached module data is removed and its entities become unavailable. A `404` from the account-wide device discovery endpoint is treated as revoked credentials and starts Home Assistant reauthentication. Registry cleanup is intentionally manual: remove the stale device from the Home Assistant device page if desired.

## Writes and diagnostics

There is no general write service in the MVP. The integration publishes only its own small encrypted `MetaInfo` record and exposes a **Sync now** button for an immediate read refresh. It exposes diagnostic entities for last update, platform, client version, capabilities, metadata and (when available) clipboard/apps. Clipboard and app entities are disabled by default; enabling them explicitly opts into exposing decrypted sensitive values to Home Assistant's state store. The dedicated diagnostics download endpoint returns redacted metadata and module shapes without decrypted values. Credentials, keysets and Authorization headers must never be exposed.

## Test shape

- Pure unit tests for linking, headers, crypto and event parsing.
- `aiohttp`/mock transport tests for status codes, ETags, reconnects and rate-limit responses.
- Home Assistant config-entry tests cover setup, unload, reauthentication and duplicate-configuration handling; API status handling, coordinator invalidation, dynamic discovery and diagnostics redaction are covered with mocks.
- A small end-to-end test against a disposable/self-hosted Octi server only when a documented test fixture is available.

### Refresh and temporary failures

The coordinator performs a five-minute HTTP safety refresh. Authenticated WebSocket `module_changed` events may request an earlier targeted refresh for the affected module, but event-triggered refreshes are coalesced for at least 30 seconds. A WebSocket disconnect triggers a full HTTP reconciliation before the next connection attempt, so missed best-effort events cannot leave the snapshot stale. A successful refresh replaces the snapshot; `304` keeps the affected module value and `204`/optional `404` removes it. Transient transport, server and rate-limit failures keep the last successful snapshot so entities do not flap to `unavailable`. A `429` uses the server's `Retry-After` value, or a conservative 15-minute cooldown when that header is absent. Reloading the config entry is the supported manual refresh operation.
