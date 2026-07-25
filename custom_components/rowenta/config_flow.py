"""Config flow for the Rowenta integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import RowentaApiError, RowentaClient
from .const import DOMAIN, LOGGER


class RowentaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Rowenta."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.host: str = ""
        self.password: str = ""
        self.robot_name: str = ""

    async def _try_connect(self, password: str) -> RowentaClient | None:
        """Attempt a connection; return the client on success, else None."""
        session = async_get_clientsession(self.hass)
        client = RowentaClient(session, self.host, password)
        try:
            connected = await client.async_connect()
        except RowentaApiError:
            LOGGER.debug("Failed to connect to Rowenta robot at %s", self.host)
            return None
        return client if connected else None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step: ask for the robot's IP address."""
        errors: dict[str, str] = {}

        if user_input:
            self.host = user_input[CONF_HOST]
            client = await self._try_connect("")

            if client is None:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(client.unique_id)
                self._abort_if_unique_id_configured()
                self.robot_name = client.display_name

                if not client.is_unlocked:
                    return await self.async_step_password()
                return self._finish(client)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): cv.string}),
            errors=errors,
        )

    async def async_step_password(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Unlock the robot's local http interface with its 8-digit code."""
        errors: dict[str, str] = {}

        if user_input:
            self.password = user_input[CONF_PASSWORD]
            client = await self._try_connect(self.password)

            if client is None or not client.is_unlocked:
                errors["base"] = "invalid_auth"
            else:
                return self._finish(client)

        return self.async_show_form(
            step_id="password",
            data_schema=vol.Schema(
                {vol.Required(CONF_PASSWORD): vol.All(cv.string, vol.Length(min=8, max=8))}
            ),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle discovery via the robot's _aicu-http._tcp.local. mDNS service."""
        self.host = discovery_info.host
        client = await self._try_connect("")

        if client is None:
            return self.async_abort(reason="cannot_connect")

        await self.async_set_unique_id(client.unique_id)
        self._abort_if_unique_id_configured(updates={CONF_HOST: self.host})

        self.robot_name = client.display_name
        self.context.update(
            {
                "title_placeholders": {"name": f"{self.robot_name} ({self.host})"},
                "configuration_url": f"http://{self.host}:{client.port}",
            }
        )

        if not client.is_unlocked:
            return await self.async_step_password()
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm adding a robot found via zeroconf discovery."""
        if user_input is None:
            return self.async_show_form(
                step_id="zeroconf_confirm",
                description_placeholders={"name": self.robot_name, "host": self.host},
            )

        client = await self._try_connect(self.password)
        if client is None:
            return self.async_abort(reason="cannot_connect")
        return self._finish(client)

    def _finish(self, client: RowentaClient) -> ConfigFlowResult:
        """Create the config entry."""
        return self.async_create_entry(
            title=self.robot_name or client.display_name,
            data={CONF_HOST: self.host, CONF_PASSWORD: self.password},
        )
