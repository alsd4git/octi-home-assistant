# MVP implementation plan

The work was deliberately split into slices that could be reviewed and tested without a complete Home Assistant integration. The current repository contains the first read-only MVP; the remaining items below are hardening or release work.

## Phase 0 — repository and protocol lock

- Confirm the repository name and codeowners; original repository code is licensed under MIT.
- Add a fixture-fetch/verify script for the SHA in `fixture-lock.json`. **Done locally:** `scripts/verify_interop_fixtures.py`.
- Record the upstream `manifest.json` digest and fail on unknown schema versions. **Done for the current pin.**
- Decide the minimum Home Assistant version and supported Python/cryptography versions.

## Phase 1 — pure protocol package

- **Done:** Implement linking payload decode/validation.
- **Done:** Implement Octi headers and URL construction.
- **Done:** Implement module payload decrypt/decompress/JSON decode.
- **Done:** Implement both keyset modes.
- **Done:** Add vector tests before adding Home Assistant imports.

## Phase 2 — transport and events

- **Done:** Add an async HTTP client with timeouts, ETags and typed errors.
- **Done:** Add authenticated WebSocket parsing for `module_changed` events.
- **Done:** Add reconnect/backoff and a bounded periodic refresh fallback.
- **Done for pure protocol paths:** Test `204`, `304`, auth failures, malformed events and reconnects.

## Phase 3 — Home Assistant integration

- **Done:** Add `manifest.json`, Config Flow, config-entry setup/unload and reauth.
- **Done:** Add one coordinator per entry.
- **Done:** Add device discovery and power/Wi-Fi/connectivity/metadata sensors.
- **Done:** Add defensive optional clipboard and installed-app diagnostics.
- **Done:** Add translations, diagnostics redaction and setup documentation.

## Phase 4 — release hardening

- **Done:** Add the validation workflow; Hassfest, Ruff, unit tests and fixture verification pass locally. HACS validation will run with the repository context in GitHub Actions.
- **Pending:** Test a clean custom-HACS install and an upgrade from the previous release in a public repository.
- **Done:** Document revocation/relinking and known limitations.
- Create the first GitHub release and ask the Octi maintainer to link the integration from ecosystem documentation once interop tests pass.

## Later candidates

- File transfer/blob support after its independent fixture suite and a clear Home Assistant UX are implemented.
- Additional optional modules and write actions only after their privacy and consent model is reviewed.
- Carefully reviewed write actions with explicit user consent.
