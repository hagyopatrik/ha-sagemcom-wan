"""Extract extra metrics (optical levels, traffic, public IP, LTE) from the data trees.

Pure Python, no Home Assistant imports. Field names verified on a
Sagemcom F@st 5670AXv2 (Telekom HU). Every value is optional: when a router
does not expose a field the metric is None and the entity is not created.
"""
from __future__ import annotations

from typing import Any

from .wan_detect import classify_interfaces, field, find_key, find_key_dict, iter_items

# TR-181 Optical units -> SI
_OPT_SCALE = {
    "optical_rx_power": ("optical_signal_level", 1000),  # 0.001 dBm
    "optical_tx_power": ("transmit_optical_level", 1000),  # 0.001 dBm
    "optical_temperature": ("temperature", 1000),  # 0.001 degC
    "optical_voltage": ("voltage", 1_000_000),  # uV
    "optical_bias_current": ("bias_current", 1000),  # uA -> mA
}


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _decode_hex(value: Any) -> str | None:
    """'5347466d313030333330' -> 'SGFm100330' (falls back to the raw value)."""
    if not value:
        return None
    s = str(value)
    try:
        text = bytes.fromhex(s).decode("ascii").strip("\x00 ")
        return text if text.isprintable() and text else s
    except ValueError:
        return s


def _optical(trees: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    iface = next(
        (i for i in iter_items(trees.get("optical")) if field(i, "optical_signal_level") is not None),
        None,
    )
    if iface is not None:
        for key, (src, div) in _OPT_SCALE.items():
            v = _num(field(iface, src))
            out[key] = round(v / div, 3) if v is not None else None
        out["optical_alarm"] = field(iface, "alarm")
        out["optical_vendor"] = field(iface, "optical_vendor_name")
    out["gpon_state"] = find_key(trees.get("optical"), "gpon_state")
    return out


def device_info(trees: dict[str, Any]) -> dict[str, Any]:
    """Model / firmware from the G.988 (OMCI) section."""
    opt = trees.get("optical")
    model = find_key(find_key_dict(opt, "onu2_g"), "equipment_id")
    sw = None
    for img in iter_items(find_key_dict(opt, "software_images")):
        if field(img, "is_active"):
            sw = _decode_hex(field(img, "version"))
    return {"model": model, "sw_version": sw}


def _day_bytes(item: dict | None) -> tuple[int | None, int | None]:
    """(received, sent) bytes of the current day (64-bit counters)."""
    day = field(field(item, "stats"), "current_day")
    rx, tx = _num(field(day, "bytes_received")), _num(field(day, "bytes_sent"))
    return (int(rx) if rx is not None else None, int(tx) if tx is not None else None)


def extract(
    trees: dict[str, Any], prev: dict[str, Any] | None, now: float
) -> dict[str, Any]:
    """Return metrics. `prev` is the previous result (for rate calculation)."""
    out: dict[str, Any] = _optical(trees)
    fiber, mobile = classify_interfaces(trees)
    data_if = fiber[0]["item"] if fiber else None
    lte_if = mobile[0]["item"] if mobile else None

    # Traffic today (counters reset by the router every day)
    rx, tx = _day_bytes(data_if)
    out["fiber_download_today"] = rx
    out["fiber_upload_today"] = tx
    lrx, ltx = _day_bytes(lte_if)
    out["mobile_download_today"] = lrx
    out["mobile_upload_today"] = ltx

    # Current throughput from counter deltas (fiber + mobile together)
    out["_ts"] = now
    out["download_rate"] = out["upload_rate"] = None
    if prev and prev.get("_ts") is not None:
        dt = now - prev["_ts"]
        if dt > 0:
            for key, a, b in (
                ("download_rate", "fiber_download_today", "mobile_download_today"),
                ("upload_rate", "fiber_upload_today", "mobile_upload_today"),
            ):
                delta, ok = 0, False
                for k in (a, b):
                    if out.get(k) is not None and prev.get(k) is not None:
                        d = out[k] - prev[k]
                        if d < 0:  # daily reset
                            ok = False
                            break
                        delta += d
                        ok = True
                if ok:
                    out[key] = round(delta * 8 / dt / 1_000_000, 2)  # Mbit/s

    # WAN link: last status change (seconds ago) and public IPv4
    out["fiber_last_change"] = _num(field(data_if, "last_change"))
    ppp = None
    for item in iter_items(trees.get("ppp")):
        if str(field(item, "connection_status") or "").upper() == "CONNECTED":
            ppp = item
            break
    out["public_ipv4"] = field(field(ppp, "ipcp"), "local_ip_address") or None
    out["wan_last_error"] = field(ppp, "last_connection_error") if ppp else None

    # LTE modem
    cell = next(iter_items(trees.get("cellular")), None)
    out["lte_modem_status"] = field(cell, "status")
    out["lte_rssi"] = _num(field(cell, "rssi"))
    return out
