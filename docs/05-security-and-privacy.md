# Security and privacy

Octi's value is end-to-end encryption. A Home Assistant integration must preserve that property as far as its local runtime can, while being honest that the decrypted values are now available to Home Assistant.

## Threat model

The main risks are:

- a linking payload or account credential copied into logs, diagnostics or bug reports;
- an attacker-controlled server URL causing unexpected cleartext transport or confusing failures;
- incorrect associated data producing plausible but unauthenticated parsing;
- broad entity exposure of clipboard, files or application data;
- a compromised Home Assistant instance reading the decrypted state.

## Rules for implementation

- Treat the linking payload as a secret. Do not include it in exception messages.
- Prefer HTTPS/WSS. An `http` endpoint is accepted only when the linking payload explicitly supplies it; the integration never downgrades an HTTPS endpoint.
- Never log Authorization, device password, keyset bytes, ciphertext or decrypted module contents.
- Keep the integration read-only until the write protocol and user-consent model are independently reviewed.
- Keep sensitive modules explicit and optional: clipboard and installed-app data are fetched only when Octi reports those module endpoints, never as a requirement for account setup. File/blob modules are not fetched.
- Verify GCM-SIV associated data exactly as specified; do not silently retry with alternate AAD values.
- Sanitize server URLs and avoid following arbitrary redirects where the HTTP client permits that control.
- Redact secrets in Home Assistant diagnostics and Config Flow error context.
- Treat WebSocket event data as a refresh hint, not as authoritative state.

## Credential lifecycle

The linking payload includes enough material to access and write the account. Even though this integration is read-only, users should be told that the linked Home Assistant device is a real Octi account participant. Re-linking or revoking that device should be documented before release.

## User-facing wording

The setup flow and README should say plainly:

> This community integration stores the Octi credentials needed to read your account. Home Assistant decrypts selected module values locally and exposes them as entities. The current release is read-only: clipboard and installed-app data may be exposed as diagnostic entities when those optional modules are available, while file transfer and blob synchronisation are not implemented.
