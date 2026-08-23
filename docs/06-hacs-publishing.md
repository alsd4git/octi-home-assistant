# HACS publishing

## Repository requirements

The integration should live in a public, dedicated GitHub repository. HACS expects the integration under one directory:

```text
custom_components/octi/
```

That directory must contain all runtime files, including `manifest.json`. The repository should also include a clear README, an explicit software license and a `hacs.json` with the integration name. The `brand/icon.png` and `brand/icon@2x.png` assets use the official Octi icon with written permission from the maintainer; they identify the Octi service and must not be presented as the logo or wordmark of this community integration. Keep the repository focused on this integration; do not bundle unrelated Home Assistant components.

The icon is sourced from the upstream Octi asset at commit [`bc9a226`](https://github.com/d4rken-org/octi/tree/bc9a2264994017b41ee2ce84d61a5337a296a878/fastlane/metadata/android/en-US/images) and is kept at both 512px (`icon@2x.png`) and 256px (`icon.png`) resolutions.

The Home Assistant manifest includes `domain`, `name`, `version`, `documentation`, `issue_tracker`, `codeowners`, `config_flow: true`, `integration_type: "hub"` and `iot_class: "cloud_push"`, matching the authenticated WebSocket listener and HTTP fallback.

## CI before publishing

The repository includes GitHub Actions for:

- Home Assistant Hassfest validation;
- HACS validation, using the `hacs/action` integration category;
- Python formatting/linting and unit tests;
- interop fixture fetching and digest verification.

The CI must not fetch an unpinned `main` branch for crypto vectors. Use the full SHA in [`fixture-lock.json`](../fixture-lock.json) and fail on digest or schema changes.

## First release path

The practical sequence is:

1. Make the repository public with a working README and issue tracker.
2. Add the integration, tests and validation workflows, including the permitted brand icon for the integrated Octi service.
3. Create a real GitHub release with a semver tag and release notes.
4. Test installation as a custom HACS repository while iterating.
5. After validation is consistently green and the integration is usable, decide whether to submit it to the HACS default catalog.

Default-catalog inclusion is optional. It requires the HACS and Hassfest checks, a full GitHub release and a pull request to `hacs/default`; a custom repository is enough for early testers.

The current HACS display name is **Octi for Home Assistant** so the community integration is not mistaken for a first-party Octi client. The technical domain remains `octi` for existing installations.

## References

- [HACS integration publishing requirements](https://www.hacs.xyz/docs/publish/integration/)
- [HACS general repository requirements](https://www.hacs.xyz/docs/publish/start/)
- [HACS validation action](https://www.hacs.xyz/docs/publish/action/)
- [Home Assistant integration manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [Home Assistant integration quality scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/)
