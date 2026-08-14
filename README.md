# Octi for Home Assistant

This repository is the working space for a Home Assistant integration for [Octi](https://github.com/d4rken-org/octi), the end-to-end encrypted device synchronisation ecosystem by d4rken.

The project is intentionally separate from both the Octi web client and the Octi Android application. The intended distribution path is a community Home Assistant integration published through [HACS](https://hacs.xyz/).

## Status

This is an early implementation workspace. A first local scaffold exists, but no Home Assistant integration is published yet.

The first milestone is a read-only integration that can:

- import an Octi linking payload;
- join an Octi account as a dedicated Home Assistant device;
- decrypt the module payloads covered by the interop fixtures;
- expose power, Wi-Fi, connectivity and device metadata entities;
- expose clipboard and installed-app information only when Octi reports the optional modules;
- refresh on authenticated Octi WebSocket events, with a polling/ETag safety net.

Writing to Octi, file transfer and encrypted blob streaming are deliberately out of scope for the MVP. Clipboard and installed-app entities are read-only diagnostic entities and may contain sensitive information.

## Documentation

- [Project brief](docs/01-project-brief.md)
- [Octi protocol notes](docs/02-octi-protocol.md)
- [Cryptography and interoperability](docs/03-crypto-and-interop.md)
- [Home Assistant architecture](docs/04-home-assistant-architecture.md)
- [Security and privacy](docs/05-security-and-privacy.md)
- [HACS publishing](docs/06-hacs-publishing.md)
- [MVP implementation plan](docs/07-mvp-plan.md)
- [Testing with Home Assistant Docker](docs/08-testing-on-home-assistant-docker.md)
- [Architecture decision: separate repository](docs/decisions/0001-separate-repository.md)

The protocol observations are based on the current Octi sources and on the maintainer discussion in [octi#370](https://github.com/d4rken-org/octi/issues/370#issuecomment-5278482391). They are working notes, not a replacement for the protocol specification planned upstream.

## Repository shape (target)

```text
custom_components/octi/
  __init__.py
  config_flow.py
  manifest.json
  coordinator.py
  api.py
  crypto.py
  sensor.py
  strings.json
  translations/en.json
brand/icon.png
hacs.json
```

The current scaffold contains the pure protocol/crypto layer, an initial Config Flow, HTTP/WebSocket client, coordinator and read-only sensors. It is not release-ready yet: it still needs broader Home Assistant version coverage, fuller module schema validation and CI packaging.

## License

The original code in this repository is released under the [MIT License](LICENSE). This license does not grant permission to reuse Octi's names, logos, icons, mascots or other excluded upstream artwork; those assets remain subject to their respective rights and licenses.
