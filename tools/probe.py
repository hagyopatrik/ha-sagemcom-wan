#!/usr/bin/env python3
"""Standalone probe for Sagemcom F@st routers (no Home Assistant needed).

    pip install sagemcom_api
    python tools/probe.py 192.168.1.1 admin "PASSWORD"

Tests login (http/https, all hash methods), prints the WAN detection and the
extra metrics, and writes sagemcom_dump.json. The dump is NOT anonymized:
use "Download diagnostics" in Home Assistant when sharing data publicly.
"""
from __future__ import annotations

import asyncio
import importlib
import json
import pathlib
import sys
import time
import types

import aiohttp
from sagemcom_api.client import SagemcomClient
from sagemcom_api.enums import EncryptionMethod

_PKG = "sagemcom_wan_pure"
_pkg = types.ModuleType(_PKG)
_pkg.__path__ = [str(pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "sagemcom_wan")]
sys.modules[_PKG] = _pkg
wd = importlib.import_module(f"{_PKG}.wan_detect")
mt = importlib.import_module(f"{_PKG}.metrics")


async def try_login(host: str, user: str, pw: str):
    for ssl in (False, True):
        for method in (EncryptionMethod.SHA512, EncryptionMethod.MD5, EncryptionMethod.MD5_NONCE):
            session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=False), timeout=aiohttp.ClientTimeout(total=20)
            )
            client = SagemcomClient(host, user, pw, method, session=session, ssl=ssl)
            try:
                await client.login()
                print(f"[OK]   login ssl={ssl} method={method}")
                return client
            except Exception as err:  # noqa: BLE001
                print(f"[FAIL] login ssl={ssl} method={method}: {type(err).__name__}")
                await session.close()
    return None


async def main(host: str, user: str, pw: str) -> None:
    client = await try_login(host, user, pw)
    if client is None:
        print(f"No working login. 404 means http(s)://{host}/cgi/json-req is not available.")
        return
    try:
        trees = {}
        for key, path in wd.QUERIES.items():
            try:
                trees[key] = await client.get_value_by_xpath(path)
                print(f"[OK]   {path}")
            except Exception as err:  # noqa: BLE001
                trees[key] = None
                print(f"[SKIP] {path}: {type(err).__name__}")
        pathlib.Path("sagemcom_dump.json").write_text(
            json.dumps(trees, indent=1, ensure_ascii=False, default=str), encoding="utf-8"
        )
        print("\n=== Detection ===")
        print(json.dumps(wd.detect(trees), indent=2, ensure_ascii=False))
        print("\n=== Metrics ===")
        m = mt.extract(trees, None, time.monotonic())
        print(json.dumps({k: v for k, v in m.items() if not k.startswith("_")}, indent=2, default=str))
        print("\n=== Device ===")
        print(mt.device_info(trees))
        print("\nRaw data written to sagemcom_dump.json (contains personal data, do not publish)")
    finally:
        try:
            await client.logout()
        except Exception:  # noqa: BLE001
            pass
        await client.close()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    asyncio.run(main(*sys.argv[1:4]))
