# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.2] - 2026-08-23

### Fixed

- Reconcile all devices and modules over HTTP after every WebSocket disconnect.
- Treat an unknown discovery caller as a reauthentication condition instead of keeping stale data.

### Documentation

- Align the protocol notes with the canonical upstream Octi reference and document the updated
  reconnect and authentication behavior.

## [0.1.1] - 2026-08-23

### Added

- Add the permitted official Octi service icon for HACS and Home Assistant branding.

### Changed

- Advertise the Home Assistant client as the generic Octi `SERVER` device type.
- Use **Octi for Home Assistant** as the public display name while keeping the `octi` domain
  unchanged for existing installations.

### Compatibility

- Octi clients older than `v1.1.0-rc0` may render the Meta tile for the `SERVER` peer as empty and
  log a decode warning; other modules continue to work.

## [0.1.0] - 2026-08-21

### Added

- Home Assistant Config Flow using an Octi linking payload, including reauthentication and
  duplicate-entry protection.
- Local decryption of supported AES-GCM-SIV and AES-SIV Octi module payloads.
- Power, Wi-Fi, connectivity and device metadata sensors.
- Optional clipboard and installed-app count diagnostics, disabled by default.
- Authenticated WebSocket refresh hints with conditional HTTP polling as a fallback.
- Dynamic device discovery, redacted diagnostics and a manual **Sync now** button.
- Publication of the Home Assistant client's encrypted `MetaInfo` record.
- Home Assistant compatibility matrix, HACS/Hassfest validation and pinned interoperability
  fixtures.

### Changed

- Register sensor entities only after their backing module fields have been observed, while keeping
  dynamic discovery for fields that appear later.

### Security

- Bounded HTTP response and gzip decompression sizes.
- Redirect rejection, diagnostics redaction and opt-in handling for sensitive entities.

[Unreleased]: https://github.com/alsd4git/octi-home-assistant/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/alsd4git/octi-home-assistant/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/alsd4git/octi-home-assistant/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/alsd4git/octi-home-assistant/releases/tag/v0.1.0
