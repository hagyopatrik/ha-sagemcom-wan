"""WAN type detection for Sagemcom F@st routers (TR-181 data model).

Pure Python, no Home Assistant imports, so it can be unit tested and reused
by the standalone probe script.
"""
from __future__ import annotations

import re
from typing import Any

# XPaths fetched for detection. Paths the router rejects are skipped.
QUERIES: dict[str, str] = {
    "routing": "Device/Routing",
    "ip": "Device/IP/Interfaces",
    "ppp": "Device/PPP/Interfaces",
    "ethernet": "Device/Ethernet",
    "optical": "Device/Optical",
    "cellular": "Device/Cellular",
}

STATE_FIBER = "fiber"
STATE_MOBILE = "mobile"
STATE_OFFLINE = "offline"
STATE_UNKNOWN = "unknown"
STATES = [STATE_FIBER, STATE_MOBILE, STATE_OFFLINE, STATE_UNKNOWN]

MOBILE_HINTS = ("cellular", "lte", "wwan", "mobile", "umts", "nr5g", "rmnet", "qmi", "mbim")
FIBER_HINTS = ("optical", "gpon", "xgspon", "xpon", "veip", "fiber", "fibre", "ftth")
# IP interfaces that are not the internet data path
NON_DATA = ("voip", "igmp", "mgmt", "mngt", "tv", "br_", "lan", "guest", "hotspot", "loopback")
MAX_DEPTH = 12


# ------------------------------------------------------------------ helpers
def _nkey(key: Any) -> str:
    """'dest_ip_address' / 'DestIPAddress' -> 'destipaddress'."""
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def _nseg(seg: str) -> str:
    """Normalize a path segment and drop plural 's' (Interfaces -> interface)."""
    s = _nkey(seg)
    return s[:-1] if s.endswith("s") and len(s) > 1 else s


def field(item: Any, name: str, default: Any = None) -> Any:
    """Case and underscore insensitive dict lookup."""
    if not isinstance(item, dict):
        return default
    target = _nkey(name)
    for k, v in item.items():
        if _nkey(k) == target:
            return v
    return default


def _find_key(node: Any, name: str) -> Any:
    """Depth-first search for the first scalar value with the given key."""
    target = _nkey(name)
    if isinstance(node, dict):
        for k, v in node.items():
            if _nkey(k) == target and not isinstance(v, (dict, list)):
                return v
            found = _find_key(v, name)
            if found is not None:
                return found
    elif isinstance(node, list):
        for v in node:
            found = _find_key(v, name)
            if found is not None:
                return found
    return None


def _iter_items(node: Any):
    if isinstance(node, list):
        for item in node:
            if isinstance(item, dict):
                yield item
    elif isinstance(node, dict):
        for v in node.values():
            if isinstance(v, (list, dict)):
                yield from _iter_items(v)


def _split_path(path: str) -> list[str]:
    sep = "/" if "/" in path else "."
    return [p for p in path.split(sep) if p]


def parse_ref(ref: str) -> tuple[str, str] | None:
    """'Device/IP/Interfaces/Interface[IP_DATA]' -> ('device/ip/interface/interface', 'ip_data').

    Also supports '[@uid=3]' and dotted 'Device.IP.Interface.3.' references.
    """
    segs = _split_path((ref or "").strip())
    sel = None
    for i, s in enumerate(segs):
        if "[" in s or s.isdigit():
            sel = i
    if sel is None:
        return None
    seg = segs[sel]
    inner = seg[seg.index("[") + 1 : seg.rindex("]")] if "[" in seg and "]" in seg else seg
    head = segs[:sel] + ([seg.split("[")[0]] if "[" in seg else [])
    container = "/".join(_nseg(s.split("[")[0]) for s in head if s and not s.isdigit())
    m = re.match(r"""@?uid\s*=\s*['"]?(\w+)['"]?""", inner, re.I)
    key = m.group(1) if m else inner.strip("'\"")
    return container, key.lower()


def _join(segs: list[str], key: str) -> list[str]:
    """Append key, skipping wrapper keys repeating the parent (ethernet/ethernet)."""
    if segs and _nseg(segs[-1]) == _nseg(key):
        return segs
    return segs + [key]


def build_index(trees: dict[str, Any]) -> dict[tuple[str, str], dict]:
    """Index every list item by (normalized container path, uid / alias / name)."""
    idx: dict[tuple[str, str], dict] = {}

    def walk(node: Any, segs: list[str]) -> None:
        if isinstance(node, list):
            # list key is plural (Interfaces), references use singular (Interface)
            cont = "/".join(_nseg(s) for s in segs)
            conts = {cont, f"{cont}/{_nseg(segs[-1])}" if segs else cont}
            for item in node:
                if not isinstance(item, dict):
                    continue
                for k in ("uid", "alias", "name"):
                    v = field(item, k)
                    if v in (None, ""):
                        continue
                    keys = {str(v).lower()}
                    parsed = parse_ref(str(v)) if k == "name" else None
                    if parsed:
                        keys.add(parsed[1])
                    for c in conts:
                        for kk in keys:
                            idx.setdefault((c, kk), item)
                for k, v in item.items():
                    if isinstance(v, (dict, list)):
                        walk(v, _join(segs, k))
        elif isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, (dict, list)):
                    walk(v, _join(segs, k))

    for base, tree in trees.items():
        if tree is not None:
            walk(tree, _split_path(base))
    return idx


def resolve(idx: dict, ref: str) -> dict | None:
    parsed = parse_ref(ref)
    return idx.get(parsed) if parsed else None


def walk_chain(idx: dict, ref: str) -> list[dict]:
    """Follow Interface -> LowerLayers references down to the physical layer."""
    chain: list[dict] = []
    seen: set[str] = set()
    todo = [(r.strip(), 0) for r in str(ref).split(",") if r.strip()]
    while todo:
        r, depth = todo.pop(0)
        if r in seen or depth > MAX_DEPTH:
            continue
        seen.add(r)
        obj = resolve(idx, r)
        parsed = parse_ref(r)
        chain.append(
            {
                "ref": r,
                "alias": field(obj, "alias") or (parsed[1].upper() if parsed else r),
                "status": field(obj, "status"),
            }
        )
        lower = field(obj, "lowerlayers") if obj else None
        if lower:
            todo.extend((x.strip(), depth + 1) for x in str(lower).split(",") if x.strip())
    return chain


def classify_chain(chain: list[dict]) -> str | None:
    tokens = [
        t
        for c in chain
        for t in re.split(r"[^a-z0-9]+", f"{c['ref']} {c['alias']}".lower())
        if t
    ]
    if any(t.startswith(h) for t in tokens for h in MOBILE_HINTS):
        return STATE_MOBILE
    if any(t.startswith(h) for t in tokens for h in FIBER_HINTS):
        return STATE_FIBER
    return None


def _is_up(value: Any) -> bool:
    return str(value or "").strip().lower() == "up"


# ---------------------------------------------------------------- detection
def detect(trees: dict[str, Any]) -> dict[str, Any]:
    """Return a dict with 'connection' in STATES plus diagnostic attributes.

    Decision is based on the status of the internet data IP interfaces
    (e.g. F@st 5670 Telekom HU):
        IP_DATA   > PPP_DATA > VLAN_DATA > GPON_DATA > OPTICAL0   (fiber)
        IP_BACKUP > LTE_MODEM                                     (mobile backup)
    """
    idx = build_index({QUERIES.get(k, k): v for k, v in trees.items()})
    gpon_state = _find_key(trees.get("optical"), "gpon_state")

    fiber: list[dict] = []
    mobile: list[dict] = []
    for item in _iter_items(trees.get("ip")):
        alias = str(field(item, "alias") or "")
        if not alias or any(h in alias.lower() for h in NON_DATA):
            continue
        chain = walk_chain(idx, f"Device/IP/Interfaces/Interface[{alias}]")
        entry = {
            "alias": alias,
            "status": str(field(item, "status") or "").upper(),
            "chain": " > ".join(str(c["alias"]) for c in chain),
        }
        kind = classify_chain(chain)
        if kind == STATE_FIBER:
            fiber.append(entry)
        elif kind == STATE_MOBILE:
            mobile.append(entry)

    fiber_up = next((e for e in fiber if _is_up(e["status"])), None)
    if fiber_up and gpon_state not in (None, "") and str(gpon_state).upper() != "OPERATIONAL":
        fiber_up = None
    mobile_up = next((e for e in mobile if _is_up(e["status"])), None)

    if fiber_up:
        conn, active = STATE_FIBER, fiber_up
    elif mobile_up:
        conn, active = STATE_MOBILE, mobile_up
    elif fiber or mobile:
        conn, active = STATE_OFFLINE, None
    else:
        conn, active = STATE_UNKNOWN, None

    return {
        "connection": conn,
        "interface": active["alias"] if active else None,
        "chain": active["chain"] if active else None,
        "fiber_status": ", ".join(f"{e['alias']}={e['status']}" for e in fiber) or None,
        "mobile_status": ", ".join(f"{e['alias']}={e['status']}" for e in mobile) or None,
        "gpon_state": gpon_state,
        "on_mobile": conn == STATE_MOBILE,
    }
