"""Diagnostics support (Settings > Devices > Download diagnostics)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import SagemcomWanConfigEntry

# Everything that can identify the user, the line or the credentials
TO_REDACT = {
    CONF_PASSWORD,
    CONF_USERNAME,
    "serial",
    "serial_number",
    "ip_address",
    "local_ip_address",
    "remote_ip_address",
    "ip_gateway",
    "public_ipv4",
    "mac_address",
    "remote_mac",
    "old_pp_po_e_session_open",
    "session_id",
    "encrypted_username",
    "encrypted_password",
    "encrypted_reg_id",
    "reg_id",
    "prefix",
    "parent_prefix",
    "child_prefix_bits",
    "local_interface_identifier",
    "remote_interface_identifier",
    "imei",
    "imsi",
    "iccid",
    "msisdn",
    "fiber_connected_since",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SagemcomWanConfigEntry
) -> dict[str, Any]:
    """Return the raw data trees so users can report unsupported models."""
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    metrics = {k: v for k, v in data.get("metrics", {}).items() if not k.startswith("_")}
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "device_info": async_redact_data(coordinator.device_info_raw, TO_REDACT),
        "detection": data.get("detection"),
        "metrics": async_redact_data(metrics, TO_REDACT),
        "raw": async_redact_data(coordinator.last_trees, TO_REDACT),
    }
