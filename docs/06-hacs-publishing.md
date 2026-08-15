# HACS publishing

## Repository requirements

The integration should live in a public, dedicated GitHub repository. HACS expects the integration under one directory:

```text
custom_components/octi/
```

That directory must contain all runtime files, including `manifest.json`. The repository should also include a clear README, an explicit software license and a `hacs.json` with the integration name. A `brand/icon.png` asset is intentionally deferred until after the MVP and written permission exists to reuse the official artwork; until then, do not copy the upstream icon because Octi explicitly excludes its artwork from the GPL license. Keep the repository focused on this integration; do not bundle unrelated Home Assistant components.

The Home Assistant manifest should include at least `domain`, `name`, `version`, `documentation`, `issue_tracker` and `codeowners`. Add `config_flow: true`, `integration_type: "hub"` and an accurate `iot_class` once the implementation exists.

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
2. Add the integration, tests and validation workflows. Add the brand icon only after the MVP and permission review.
3. Create a real GitHub release with a semver tag and release notes.
4. Test installation as a custom HACS repository while iterating.
5. After validation is consistently green and the integration is usable, decide whether to submit it to the HACS default catalog.

Default-catalog inclusion is optional. It requires the HACS and Hassfest checks, a full GitHub release and a pull request to `hacs/default`; a custom repository is enough for early testers.

## References

- [HACS integration publishing requirements](https://www.hacs.xyz/docs/publish/integration/)
- [HACS general repository requirements](https://www.hacs.xyz/docs/publish/start/)
- [HACS validation action](https://www.hacs.xyz/docs/publish/action/)
- [Home Assistant integration manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [Home Assistant integration quality scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/)
