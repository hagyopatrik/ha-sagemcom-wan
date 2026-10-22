"""Unit tests for wan_detect (run: python -m pytest tests)."""
import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "wan_detect",
    pathlib.Path(__file__).parents[1] / "custom_components" / "sagemcom_wan" / "wan_detect.py",
)
wd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wd)


def fast5670(fiber_ok: bool) -> dict:
    """Data shape as returned by a Sagemcom F@st 5670 (Telekom HU)."""
    return {
        "routing": None,  # Device/Routing is not exposed on this firmware
        "ip": [
            {"alias": "IP_BR_LAN", "status": "UP", "lower_layers": "Device/Ethernet/Links/Link[ETHLNK_BR_LAN]"},
            {"alias": "IP_DATA", "status": "UP" if fiber_ok else "LOWERLAYERDOWN",
             "lower_layers": "Device/PPP/Interfaces/Interface[PPP_DATA]"},
            {"alias": "IP_VOIP", "status": "UP",
             "lower_layers": "Device/Ethernet/VLANTerminations/VLANTermination[VLAN_VOIP]"},
            {"alias": "IP_BACKUP", "status": "LOWERLAYERDOWN" if fiber_ok else "UP",
             "lower_layers": "Device/Cellular/Interfaces/Interface[LTE_MODEM]"},
        ],
        "ppp": [
            {"alias": "PPP_DATA", "status": "UP",
             "lower_layers": "Device/Ethernet/VLANTerminations/VLANTermination[VLAN_DATA]"},
        ],
        "ethernet": {"ethernet": {
            "links": [
                {"alias": "FTTH_DATA", "lower_layers": "Device/Ethernet/Interfaces/Interface[PHY5]"},
                {"alias": "GPON_DATA", "lower_layers": "Device/Optical/Interfaces/Interface[OPTICAL0]"},
            ],
            "interfaces": [{"alias": "PHY5"}],
            "vlan_terminations": [
                {"alias": "VLAN_DATA",
                 "lower_layers": "Device/Ethernet/Links/Link[FTTH_DATA],Device/Ethernet/Links/Link[GPON_DATA]"},
            ],
        }},
        "optical": {"optical": {"interfaces": [{"alias": "OPTICAL0"}],
                                "G988": {"gpon_state": "OPERATIONAL" if fiber_ok else "LOS"}}},
        "cellular": {"cellular": {"interfaces": [{"alias": "LTE_MODEM"}]}},
    }


def test_fiber():
    r = wd.detect(fast5670(True))
    assert r["connection"] == "fiber"
    assert r["interface"] == "IP_DATA"
    assert r["chain"].endswith("OPTICAL0")
    assert r["on_mobile"] is False


def test_mobile_backup():
    r = wd.detect(fast5670(False))
    assert r["connection"] == "mobile"
    assert r["interface"] == "IP_BACKUP"
    assert r["on_mobile"] is True


def test_offline():
    data = fast5670(False)
    data["ip"][3]["status"] = "LOWERLAYERDOWN"
    assert wd.detect(data)["connection"] == "offline"


def test_unknown_when_empty():
    assert wd.detect({"ip": []})["connection"] == "unknown"
