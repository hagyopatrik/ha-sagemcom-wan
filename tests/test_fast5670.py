"""Tests with the data layout of a Sagemcom F@st 5670AXv2 (Telekom HU).

The fixture uses the field names and values seen on a real router;
addresses are replaced with documentation ranges.
"""
import copy
import json
import pathlib

from conftest import metrics, wan_detect

FIXTURE = json.loads((pathlib.Path(__file__).parent / "fixtures" / "fast5670_fiber.json").read_text())


def _ip(trees, alias):
    return next(i for i in trees["ip"] if i["alias"] == alias)


def test_detect_fiber():
    r = wan_detect.detect(FIXTURE)
    assert r["connection"] == "fiber"
    assert r["interface"] == "IP_DATA"
    assert r["chain"].endswith("OPTICAL0")
    assert r["gpon_state"] == "OPERATIONAL"


def test_detect_mobile_backup():
    t = copy.deepcopy(FIXTURE)
    _ip(t, "IP_DATA")["status"] = "LOWERLAYERDOWN"
    _ip(t, "IP_BACKUP")["status"] = "UP"
    t["optical"]["optical"]["G988"]["gpon_state"] = "LOS"
    r = wan_detect.detect(t)
    assert r["connection"] == "mobile"
    assert r["on_mobile"] is True


def test_detect_offline():
    t = copy.deepcopy(FIXTURE)
    _ip(t, "IP_DATA")["status"] = "LOWERLAYERDOWN"
    assert wan_detect.detect(t)["connection"] == "offline"


def test_optical_metrics():
    m = metrics.extract(FIXTURE, None, 0.0)
    assert m["optical_rx_power"] == -25.85
    assert m["optical_tx_power"] == 3.317
    assert m["optical_temperature"] == 30.257
    assert m["optical_voltage"] == 3.307
    assert m["optical_bias_current"] == 14.35
    assert m["optical_alarm"] == "NONE"


def test_traffic_and_wan():
    m = metrics.extract(FIXTURE, None, 0.0)
    assert m["fiber_download_today"] == 11845780220
    assert m["mobile_download_today"] == 31010373
    assert m["public_ipv4"] == "192.0.2.10"
    assert m["fiber_last_change"] == 4544
    assert m["wan_last_error"] == "ERROR_NONE"
    assert m["lte_modem_status"] == "DORMANT"
    assert m["download_rate"] is None  # no previous sample


def test_rates():
    m1 = metrics.extract(FIXTURE, None, 100.0)
    t = copy.deepcopy(FIXTURE)
    day = _ip(t, "IP_DATA")["stats"]["current_day"]
    day["bytes_received"] = str(int(day["bytes_received"]) + 125_000_000)  # 100 Mbit in 10 s
    day["bytes_sent"] = str(int(day["bytes_sent"]) + 12_500_000)
    m2 = metrics.extract(t, m1, 110.0)
    assert m2["download_rate"] == 100.0
    assert m2["upload_rate"] == 10.0


def test_rate_daily_reset():
    m1 = metrics.extract(FIXTURE, None, 0.0)
    t = copy.deepcopy(FIXTURE)
    _ip(t, "IP_DATA")["stats"]["current_day"]["bytes_received"] = "1000"
    assert metrics.extract(t, m1, 30.0)["download_rate"] is None


def test_device_info():
    assert metrics.device_info(FIXTURE) == {"model": "Fast5670AXv2", "sw_version": "SGFm100330"}
