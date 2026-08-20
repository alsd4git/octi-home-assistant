# Project brief

## Why this exists

Octi already provides a useful encrypted bridge between devices. Home Assistant is a natural always-on consumer for the same device state, but the existing web client is not a good integration boundary: it is a browser application, it depends on browser-specific linking and visibility behaviour, and it is not part of the Home Assistant runtime.

The Octi maintainer has indicated that a separate community repository with HACS distribution is the preferred shape for this work. See [octi#370](https://github.com/d4rken-org/octi/issues/370#issuecomment-5278482391).

## First user story

> I paste an Octi linking payload into Home Assistant and see the current power, Wi-Fi and connectivity state of my linked devices without exposing the Octi credentials in logs or requiring a browser tab to stay open.

## MVP scope

The first release should be read-mostly and intentionally narrow:

1. A config flow accepts the Octi linking payload and validates its server, share code and keyset.
2. The integration joins the account with a stable Home Assistant device identity.
3. It discovers linked Octi devices and reads the core power, Wi-Fi, connectivity and metadata modules.
4. It decrypts both account keyset modes covered by the upstream fixtures.
5. It listens to `/v1/ws` and performs a debounced refresh for `module_changed` events.
6. It falls back to conditional HTTP requests on reconnect and at a conservative interval.
7. It exposes optional clipboard and installed-app count diagnostics when those modules are available.

## Non-goals for the MVP

- Mutating peer Octi state or exposing general write services. Publishing the Home Assistant client's own encrypted `MetaInfo` is the only exception.
- File contents, file transfer and other write-oriented or high-risk modules. Clipboard contents and installed-app count are optional read-only diagnostics and must remain clearly marked as sensitive.
- Streaming blob encryption/decryption.
- Reimplementing account management or inventing a new linking format.
- Claiming official Home Assistant or official Octi support.

## Success criteria

- A fresh installation can be configured from a documented linking flow.
- Interoperability tests pass against the pinned upstream vectors for every supported encryption mode.
- A temporary network failure does not create duplicate entities or lose the config entry.
- Secrets are stored using Home Assistant's config-entry machinery and never appear in normal logs.
- HACS validation and Home Assistant's Hassfest checks pass before the first release.
- The README clearly labels the integration as community-maintained and read-mostly, with the self-`MetaInfo` exception.

## Current operational decisions

- Devices removed from the Octi account are not deleted automatically from the Home Assistant registry. Their entities become unavailable and users remove the registry entry manually when needed.

The current minimum tested baseline is Home Assistant `2026.2.3` with Python `>=3.13.2`. Home Assistant `2026.8.2` is also covered by CI with Python 3.14. Intermediate `2026.x` releases are expected to work from the baseline but are not individually claimed as tested. The integration manifest does not support a minimum-version key, so this policy is documented and enforced through the test matrix.
