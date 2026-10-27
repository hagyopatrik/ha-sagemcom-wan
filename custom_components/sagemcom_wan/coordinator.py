"""Data update coordinator for the Sagemcom F@st WAN integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
import time
from typing import Any

from sagemcom_api.client import SagemcomClient
from sagemcom_api.exceptions import AccessRestrictionException, UnknownPathException

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .metrics import device_info, extract
from .wan_detect import QUERIES, detect, field

_LOGGER = logging.getLogger(__name__)

# Ignore jitter of the computed "connected since" timestamp below this
SINCE_TOLERANCE = 90  # seconds


class SagemcomWanCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the router; data = {'detection': {...}, 'metrics': {...}}."""

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
        self._prev_metrics: dict[str, Any] | None = None
        self._since: datetime | None = None
        self.device_info_raw: dict[str, Any] = {}
        self.last_trees: dict[str, Any] = {}

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
            }
        except Exception as err:  # noqa: BLE001 - optional information only
            _LOGGER.debug("Could not read Device/DeviceInfo: %s", err)

    def _connected_since(self, seconds_ago: float | None) -> datetime | None:
        if seconds_ago is None or seconds_ago <= 0:
            return self._since if seconds_ago is None else None
        since = (dt_util.utcnow() - timedelta(seconds=seconds_ago)).replace(microsecond=0)
        if self._since is None or abs((since - self._since).total_seconds()) > SINCE_TOLERANCE:
            self._since = since
        return self._since

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
        except Exception as err:  # noqa: BLE001
            self._logged_in = False
            raise UpdateFailed(f"{type(err).__name__}: {err}") from err

        self.last_trees = trees
        if not self.device_info_raw.get("model"):
            fallback = device_info(trees)
            self.device_info_raw = {**fallback, **{k: v for k, v in self.device_info_raw.items() if v}}

        metrics = extract(trees, self._prev_metrics, time.monotonic())
        self._prev_metrics = metrics
        metrics["fiber_connected_since"] = self._connected_since(metrics.get("fiber_last_change"))
        return {"detection": detect(trees), "metrics": metrics}

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
