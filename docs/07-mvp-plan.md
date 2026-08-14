# MVP implementation plan

The work is deliberately split into slices that can be reviewed and tested without a complete Home Assistant integration.

## Phase 0 — repository and protocol lock

- Confirm the repository name, license and codeowners.
- Add a fixture-fetch/verify script for the SHA in `fixture-lock.json`. **Done locally:** `scripts/verify_interop_fixtures.py`.
- Record the upstream `manifest.json` digest and fail on unknown schema versions. **Done for the current pin.**
- Decide the minimum Home Assistant version and supported Python/cryptography versions.

## Phase 1 — pure protocol package

- Implement linking payload decode/validation.
- Implement Octi headers and URL construction.
- Implement module payload decrypt/decompress/JSON decode.
- Implement both keyset modes, or a clear temporary legacy rejection.
- Add vector tests before adding Home Assistant imports.

## Phase 2 — transport and events

- Add an async HTTP client with timeouts, ETags and typed errors.
- Add authenticated WebSocket parsing for `module_changed` events.
- Add reconnect/backoff and a bounded periodic refresh fallback.
- Test `204`, `304`, auth failures, malformed events and reconnects.

## Phase 3 — Home Assistant integration

- Add `manifest.json`, Config Flow, config-entry setup/unload and reauth.
- Add one coordinator per entry.
- Add device discovery and power/Wi-Fi/connectivity/metadata sensors.
- Add defensive optional clipboard and installed-app diagnostics.
- Add translations, diagnostics redaction and setup documentation.

## Phase 4 — release hardening

- Run Hassfest, HACS validation, lint and tests in CI.
- Test a clean custom-HACS install and an upgrade from the previous release.
- Document revocation/relinking and known limitations.
- Create the first GitHub release and ask the Octi maintainer to link the integration from ecosystem documentation once interop tests pass.

## Later candidates

- File transfer/blob support after its independent fixture suite and a clear Home Assistant UX are implemented.
- Additional optional modules and write actions only after their privacy and consent model is reviewed.
- Carefully reviewed write actions with explicit user consent.
