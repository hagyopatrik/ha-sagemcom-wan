"""Synthetic tests for wan_detect."""
from conftest import wan_detect as wd


def test_unknown_when_empty():
    assert wd.detect({"ip": []})["connection"] == "unknown"


def test_parse_ref_variants():
    assert wd.parse_ref("Device/IP/Interfaces/Interface[IP_DATA]")[1] == "ip_data"
    assert wd.parse_ref("Device/IP/Interfaces/Interface[@uid=3]")[1] == "3"
    assert wd.parse_ref("Device.IP.Interface.3.")[1] == "3"
