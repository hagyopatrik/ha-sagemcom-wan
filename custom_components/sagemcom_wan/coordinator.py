"""Data update coordinator for the Sagemcom F@st WAN integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from sagemcom_api.client import SagemcomClient
from sagemcom_api.exceptions import (
    AccessRestrictionException,
    UnknownPathException,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .wan_detect import QUERIES, detect, field

_LOGGER = logging.getLogger(__name__)


class SagemcomWanCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the router and compute the active WAN type."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: SagemcomClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client
        self._logged_in = False
        self._skip_paths: set[str] = set()
        self.device_info_raw: dict[str, Any] = {}

    async def _ensure_login(self) -> None:
        if not self._logged_in:
            await self.client.login()
            self._logged_in = True

    async def async_fetch_device_info(self) -> None:
        """Best effort read of model / firmware for the device registry."""
        try:
            await self._ensure_login()
            info = await self.client.get_value_by_xpath("Device/DeviceInfo")
            self.device_info_raw = {
                "model": field(info, "modelname") or field(info, "productclass"),
                "sw_version": field(info, "softwareversion"),
                "hw_version": field(info, "hardwareversion"),
                "serial": field(info, "serialnumber"),
            }
        except Exception as err:  # noqa: BLE001 - optional information only
            _LOGGER.debug("Could not read Device/DeviceInfo: %s", err)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            await self._ensure_login()
            trees: dict[str, Any] = {}
            for key, path in QUERIES.items():
                if path in self._skip_paths:
                    continue
                try:
                    trees[key] = await self.client.get_value_by_xpath(path)
                except (UnknownPathException, AccessRestrictionException) as err:
                    _LOGGER.debug("Skipping %s: %s", path, type(err).__name__)
                    self._skip_paths.add(path)
            return detect(trees)
        except Exception as err:  # noqa: BLE001
            self._logged_in = False
            raise UpdateFailed(f"{type(err).__name__}: {err}") from err

    async def async_shutdown(self) -> None:
        """Log out and close the session."""
        await super().async_shutdown()
        if self._logged_in:
            try:
                await self.client.logout()
            except Exception:  # noqa: BLE001
                pass
            self._logged_in = False
        await self.client.close()
