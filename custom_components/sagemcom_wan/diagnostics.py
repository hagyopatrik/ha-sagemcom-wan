"""Diagnostics support (Settings > Devices > Download diagnostics)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import SagemcomWanConfigEntry
from .wan_detect import QUERIES

TO_REDACT = {CONF_PASSWORD, CONF_USERNAME, "serial", "serial_number", "ip_address",
             "mac_address", "imei", "imsi", "iccid", "username", "password"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SagemcomWanConfigEntry
) -> dict[str, Any]:
    """Return the raw data trees so users can report unsupported models."""
    coordinator = entry.runtime_data
    raw: dict[str, Any] = {}
    for key, path in QUERIES.items():
        try:
            raw[key] = await coordinator.client.get_value_by_xpath(path)
        except Exception as err:  # noqa: BLE001
            raw[key] = f"error: {type(err).__name__}"
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "device_info": async_redact_data(coordinator.device_info_raw, TO_REDACT),
        "detection": coordinator.data,
        "raw": async_redact_data(raw, TO_REDACT),
    }
