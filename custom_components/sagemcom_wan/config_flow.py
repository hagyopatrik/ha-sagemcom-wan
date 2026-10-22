"""Config flow for the Sagemcom F@st WAN integration."""
from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError
from sagemcom_api.exceptions import (
    AuthenticationException,
    LoginConnectionException,
    LoginRetryErrorException,
    LoginTimeoutException,
    MaximumSessionCountException,
    UnauthorizedException,
    UnsupportedHostException,
)
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_SSL, CONF_USERNAME, CONF_VERIFY_SSL
from homeassistant.core import callback

from .client import async_detect_and_login, create_client
from .const import (
    CONF_ENCRYPTION_METHOD,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
    ENCRYPTION_AUTO,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default="192.168.1.1"): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_SSL, default=False): bool,
        vol.Optional(CONF_VERIFY_SSL, default=False): bool,
    }
)


class SagemcomWanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST].strip().lower())
            self._abort_if_unique_id_configured()

            data = {**user_input, CONF_ENCRYPTION_METHOD: ENCRYPTION_AUTO}
            client = create_client(self.hass, data)
            try:
                method = await async_detect_and_login(client)
                if method is None:
                    errors["base"] = "invalid_auth"
                else:
                    try:
                        await client.logout()
                    except Exception:  # noqa: BLE001
                        pass
            except (AuthenticationException, UnauthorizedException, LoginRetryErrorException):
                errors["base"] = "invalid_auth"
            except MaximumSessionCountException:
                errors["base"] = "too_many_sessions"
            except UnsupportedHostException:
                errors["base"] = "unsupported"
            except (LoginConnectionException, LoginTimeoutException, ClientError, TimeoutError, ConnectionError):
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during login")
                errors["base"] = "unknown"
            finally:
                await client.close()

            if not errors:
                data[CONF_ENCRYPTION_METHOD] = method
                return self.async_create_entry(title=f"Sagemcom F@st ({user_input[CONF_HOST]})", data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SagemcomWanOptionsFlow()


class SagemcomWanOptionsFlow(OptionsFlow):
    """Options: polling interval."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                        vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                    )
                }
            ),
        )
