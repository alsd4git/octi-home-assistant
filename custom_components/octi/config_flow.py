"""Config flow for Octi."""

from __future__ import annotations

import base64
import uuid
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OctiApiClient, OctiApiError, OctiAuthenticationError
from .const import (
    CONF_ACCOUNT_ID,
    CONF_DEVICE_ID,
    CONF_DEVICE_PASSWORD,
    CONF_KEYSET,
    CONF_KEYSET_TYPE,
    CONF_SERVER,
    DOMAIN,
)
from .linking import LinkingData, LinkingPayloadError, decode_linking_payload


class OctiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Octi setup through a pasted linking payload."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                linking = decode_linking_payload(user_input["linking_payload"])
                result = await self._async_join(linking)
                account_id = _credential(result, "account")
                device_password = _credential(result, "password")
            except LinkingPayloadError as err:
                errors["base"] = _linking_error(err)
            except OctiAuthenticationError:
                errors["base"] = "invalid_auth"
            except OctiApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{linking.server}:{account_id}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Octi ({account_id[:8]})",
                    data={
                        CONF_SERVER: linking.server,
                        CONF_ACCOUNT_ID: account_id,
                        CONF_DEVICE_PASSWORD: device_password,
                        CONF_DEVICE_ID: self._device_id,
                        CONF_KEYSET_TYPE: linking.keyset_type,
                        CONF_KEYSET: base64.b64encode(linking.keyset).decode(),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("linking_payload"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle reauthentication for an existing config entry."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                linking = decode_linking_payload(user_input["linking_payload"])
                if linking.server != entry.data[CONF_SERVER]:
                    raise LinkingPayloadError("The server does not match this entry")
                result = await self._async_join(linking, entry.data[CONF_DEVICE_ID])
                account_id = _credential(result, "account")
                device_password = _credential(result, "password")
                if account_id != entry.data[CONF_ACCOUNT_ID]:
                    raise LinkingPayloadError("The account does not match this entry")
            except LinkingPayloadError as err:
                errors["base"] = _linking_error(err)
            except OctiAuthenticationError:
                errors["base"] = "invalid_auth"
            except OctiApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_SERVER: linking.server,
                        CONF_ACCOUNT_ID: account_id,
                        CONF_DEVICE_PASSWORD: device_password,
                        CONF_DEVICE_ID: self._device_id,
                        CONF_KEYSET_TYPE: linking.keyset_type,
                        CONF_KEYSET: base64.b64encode(linking.keyset).decode(),
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required("linking_payload"): str,
                }
            ),
            errors=errors,
        )

    async def _async_join(
        self, linking: LinkingData, device_id: str | None = None
    ) -> dict[str, Any]:
        self._device_id = device_id or str(uuid.uuid4())
        client = OctiApiClient(
            session=async_get_clientsession(self.hass),
            server=linking.server,
            account_id="pending",
            device_password="pending",
            device_id=self._device_id,
            keyset=linking.keyset,
            keyset_type=linking.keyset_type,
        )
        try:
            return await client.async_join_account(linking.share_code)
        finally:
            await client.async_close()


def _credential(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise OctiApiError("Octi did not return account credentials")
    return value


def _linking_error(error: LinkingPayloadError) -> str:
    message = str(error)
    if "not supported" in message:
        return "unsupported_encryption"
    return "invalid_payload"
