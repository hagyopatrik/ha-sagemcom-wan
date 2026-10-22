"""Helpers to create and log in a Sagemcom API client."""
from __future__ import annotations

from typing import Any

from sagemcom_api.client import SagemcomClient
from sagemcom_api.enums import EncryptionMethod

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_SSL, CONF_USERNAME, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import CONF_ENCRYPTION_METHOD, ENCRYPTION_AUTO


def create_client(hass: HomeAssistant, data: dict[str, Any]) -> SagemcomClient:
    """Create a client with a dedicated aiohttp session."""
    method = data.get(CONF_ENCRYPTION_METHOD, ENCRYPTION_AUTO)
    session = async_create_clientsession(hass, verify_ssl=data.get(CONF_VERIFY_SSL, False))
    return SagemcomClient(
        data[CONF_HOST],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        None if method == ENCRYPTION_AUTO else EncryptionMethod(method),
        session=session,
        ssl=data.get(CONF_SSL, False),
    )


async def async_detect_and_login(client: SagemcomClient) -> str | None:
    """Find the working encryption method, log in and return the method name."""
    method = await client.get_encryption_method()
    if method is None:
        return None
    await client.login()
    return str(method)
