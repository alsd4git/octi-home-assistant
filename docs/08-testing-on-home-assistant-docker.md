# Testing the integration with Home Assistant Docker

This project is not published through HACS yet. Install it as a local custom integration while developing.

## 1. Find the Home Assistant config volume

On the Linux host, identify the container and its `/config` mount:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
docker inspect <home-assistant-container> \\
  --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'
```

Use the host path mapped to `/config`. In a Compose setup it is often a directory such as `./config` next to `docker-compose.yml`.

## 2. Install the component

The persistent host-volume method is preferred:

```bash
mkdir -p <ha-config-dir>/custom_components/octi
cp -a custom_components/octi/. <ha-config-dir>/custom_components/octi/
```

Run the copy from the project root, or replace `custom_components/octi` with its absolute path. Copy only the integration directory; the Python project files and tests are not needed by Home Assistant.

For a quick disposable test, the same files can be copied directly into the container:

```bash
docker exec <home-assistant-container> mkdir -p /config/custom_components/octi
docker cp custom_components/octi/. \\
  <home-assistant-container>:/config/custom_components/octi/
```

`docker cp` is suitable for a first check but changes can be lost if `/config` is not backed by a persistent volume. Do not use it as the long-term development workflow unless the container mount is persistent.

Verify the final layout:

```bash
docker exec <home-assistant-container> \\
  find /config/custom_components/octi -maxdepth 2 -type f -print
```

The directory must contain `manifest.json` and `__init__.py` directly, not an extra nested `octi/octi` directory.

## 3. Restart Home Assistant

With Compose:

```bash
docker compose restart <home-assistant-service>
```

With a standalone container:

```bash
docker restart <home-assistant-container>
```

Watch startup logs:

```bash
docker logs -f --tail=200 <home-assistant-container> \\
  | grep -iE 'octi|custom_components|error|exception'
```

Do not add `octi:` to `configuration.yaml`; this integration is configured through the UI. If Home Assistant does not list Octi after a restart, check the path and the logs first.

## 4. Configure it from the UI

In Home Assistant:

1. Open **Settings → Devices & services**.
2. Select **Add integration**.
3. Search for **Octi**.
4. Paste the complete Octi linking payload.

The linking payload is sensitive: it contains the account credentials and encryption keyset. Do not paste it into an issue or a shared terminal transcript.

The current integration is read-only and exposes power, Wi-Fi, connectivity and metadata sensors. Clipboard and installed-app entities are added only when the corresponding optional Octi modules return data. It joins the Octi account as a separate Home Assistant device and attempts an authenticated WebSocket connection, with HTTP refresh as a fallback.

## 5. Collect useful diagnostics

If setup fails, collect only the relevant log lines and redact account IDs, passwords, linking payloads, Authorization headers and key material:

```bash
docker logs --since=10m <home-assistant-container> 2>&1 \\
  | grep -iE 'octi|config_flow|custom_components|tink|exception|traceback'
```

The runtime crypto implementation uses Home Assistant's existing `cryptography` dependency. Check it directly if needed:

```bash
docker exec <home-assistant-container> \\
  python -c 'import cryptography; print(cryptography.__version__)'
```

Do not install extra native build tools or a separate Tink package manually in the container. The custom integration must remain installable on the existing Home Assistant image.

## Current limitations

- The supported baseline is Home Assistant 2026.2.3; the test harness runs against that version while the live Docker host currently runs a newer release.
- Dynamic discovery of devices added after the initial setup is implemented; registry cleanup for removed devices still needs hardening.
- HACS metadata and CI are present. The brand asset/icon is intentionally deferred until after the MVP and permission review; default-catalog publication also waits for a public repository, release and brand review.
