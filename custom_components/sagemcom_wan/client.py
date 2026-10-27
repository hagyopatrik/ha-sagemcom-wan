"""Helpers to create and log in a Sagemcom API client."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from sagemcom_api.client import SagemcomClient
from sagemcom_api.enums import EncryptionMethod
from sagemcom_api.exceptions import (
    AuthenticationException,
    LoginRetryErrorException,
    LoginTimeoutException,
    UnauthorizedException,
)

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_SSL, CONF_USERNAME, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import CONF_ENCRYPTION_METHOD, ENCRYPTION_AUTO

_LOGGER = logging.getLogger(__name__)

# SHA512 first: recent F@st models (e.g. 5670) use it, and every attempt with a
# wrong method counts as a failed login on the router (which then throttles).
METHOD_ORDER = [EncryptionMethod.SHA512, EncryptionMethod.MD5, EncryptionMethod.MD5_NONCE]
RETRY_DELAY = 5  # seconds to wait after XMO_LOGIN_RETRY_ERR


def create_client(
    hass: HomeAssistant, data: dict[str, Any], method: EncryptionMethod | None = None
) -> SagemcomClient:
    """Create a client with its own aiohttp session."""
    if method is None:
        stored = data.get(CONF_ENCRYPTION_METHOD, ENCRYPTION_AUTO)
        method = None if stored == ENCRYPTION_AUTO else EncryptionMethod(stored)
    session = async_create_clientsession(hass, verify_ssl=data.get(CONF_VERIFY_SSL, False))
    return SagemcomClient(
        data[CONF_HOST],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        method,
        session=session,
        ssl=data.get(CONF_SSL, False),
    )


async def async_find_method(hass: HomeAssistant, data: dict[str, Any]) -> EncryptionMethod:
    """Try every hash method with a FRESH client and return the working one."""
    last_err: Exception | None = None
    auth_failed = False
    for method in METHOD_ORDER:
        for _attempt in range(2):
            client = create_client(hass, data, method)
            try:
                await client.login()
                _LOGGER.debug("Login OK with %s", method)
                try:
                    await client.logout()
                except Exception:  # noqa: BLE001
                    pass
                return method
            except LoginRetryErrorException as err:
                _LOGGER.debug("Login throttled with %s, retrying in %ss", method, RETRY_DELAY)
                last_err = err
                await asyncio.sleep(RETRY_DELAY)
                continue
            except (AuthenticationException, UnauthorizedException, LoginTimeoutException) as err:
                _LOGGER.debug("Login with %s failed: %s", method, err)
                auth_failed = True
                last_err = err
                break
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Login with %s error: %s: %s", method, type(err).__name__, err)
                raise
            finally:
                await client.close()
    if auth_failed or last_err is None:
        raise AuthenticationException("No encryption method accepted the credentials")
    raise last_err
