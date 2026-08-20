# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/alsd4git/octi-home-assistant/compare/v0.1.0...HEAD
