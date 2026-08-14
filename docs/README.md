# Documentation map

These documents capture the decisions and facts needed to build the integration without turning the issue discussion into an implicit specification.

| Document | Purpose |
| --- | --- |
| [Project brief](01-project-brief.md) | Scope, users, success criteria and non-goals |
| [Octi protocol notes](02-octi-protocol.md) | HTTP, linking, headers, modules and WebSocket observations |
| [Cryptography and interoperability](03-crypto-and-interop.md) | Keyset modes, payload format and fixture-driven tests |
| [Home Assistant architecture](04-home-assistant-architecture.md) | Config flow, storage, coordinator and entity model |
| [Security and privacy](05-security-and-privacy.md) | Threat model and operational rules |
| [HACS publishing](06-hacs-publishing.md) | Repository layout, validation and release path |
| [MVP implementation plan](07-mvp-plan.md) | Small, reviewable implementation slices |
| [Testing with Home Assistant Docker](08-testing-on-home-assistant-docker.md) | Local installation and diagnostics workflow |

Protocol statements should be checked against the upstream sources and interop fixtures whenever the pinned Octi commit changes.
