"""Config flow for the Aprilaire Cloud integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pyaprilaire_cloud.client import (
    AprilaireCloudClient,
    CloudClientAuthError,
    CloudClientRequestError,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): str})


class NoDevicesError(Exception):
    """The account has no devices."""


class AprilaireCloudConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    async def _async_validate(self, username: str, password: str) -> None:
        """Validate credentials and that the account has devices."""
        client = AprilaireCloudClient(
            username,
            password,
            _LOGGER,
            session=async_get_clientsession(self.hass),
        )
        await client.authenticate()
        hierarchy = await client.get_hierarchy()
        if not hierarchy.device_ids:
            raise NoDevicesError

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            try:
                await self._async_validate(username, user_input[CONF_PASSWORD])
            except CloudClientAuthError:
                errors["base"] = "invalid_auth"
            except CloudClientRequestError:
                errors["base"] = "cannot_connect"
            except NoDevicesError:
                return self.async_abort(reason="no_devices")
            except Exception:
                _LOGGER.exception("Unexpected error validating credentials")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(username.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=username,
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth when credentials stop working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new password and revalidate."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            try:
                await self._async_validate(
                    reauth_entry.data[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
            except CloudClientAuthError:
                errors["base"] = "invalid_auth"
            except CloudClientRequestError:
                errors["base"] = "cannot_connect"
            except NoDevicesError:
                return self.async_abort(reason="no_devices")
            except Exception:
                _LOGGER.exception("Unexpected error validating credentials")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            description_placeholders={CONF_USERNAME: reauth_entry.data[CONF_USERNAME]},
            errors=errors,
        )
