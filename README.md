# Sagemcom F@st WAN Monitor

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![Validate](https://github.com/hagyopatrik/ha-sagemcom-wan/actions/workflows/validate.yml/badge.svg)](https://github.com/hagyopatrik/ha-sagemcom-wan/actions/workflows/validate.yml)

Home Assistant integration for **Sagemcom F@st** routers: shows whether the router is connected
through **fiber (GPON)** or its **LTE mobile backup**, plus optical signal levels, traffic and WAN details.

Built and tested on the **Sagemcom F@st 5670AXv2** (Telekom Hungary). Other F@st models that use the
`/cgi/json-req` API and the TR-181 data model should work; sensors are only created for data the
router actually exposes.

> [!IMPORTANT]
> **The router's web interface (web GUI) may be inaccessible while this Home Assistant integration is running.**
> If you need to log in to the router's web interface, stop/disable the integration and wait approximately **1 minute**.
> You should then be able to log in normally. Remember to start the integration again afterward.

## Sensors

| Sensor | Unit | Notes |
|---|---|---|
| Connection type | `fiber` / `mobile` / `offline` / `unknown` | attribute `on_mobile` for automations |
| Optical RX power | dBm | received light level from the fiber |
| Optical TX power | dBm | |
| Download / upload rate | Mbit/s | calculated from WAN counters between polls |
| Fiber download / upload today | GB | resets daily (router counter) |
| Mobile download / upload today | GB | LTE backup data usage |
| Public IPv4 address | | |
| Fiber connected since | timestamp | last status change of the fiber WAN interface |
| LTE modem status | | e.g. `DORMANT` while on fiber |
| GPON state, optical alarm, WAN last error | | diagnostic |
| Optical module temperature, voltage, bias current, LTE RSSI (raw) | | diagnostic, voltage/bias disabled by default |

## Installation

### HACS (recommended)

1. HACS → three dots menu → **Custom repositories**
2. Repository: `https://github.com/hagyopatrik/ha-sagemcom-wan`, Type: **Integration**
3. Install **Sagemcom F@st WAN Monitor** and restart Home Assistant

### Manual

Copy `custom_components/sagemcom_wan` to `/config/custom_components/` and restart Home Assistant.

## Configuration

**Settings → Devices & services → Add integration → Sagemcom F@st WAN Monitor**

| Field | F@st 5670AXv2 (Telekom HU) |
|---|---|
| Host | `192.168.1.1` |
| Username | `admin` |
| Password | router admin password |
| Use HTTPS | off |

Polling interval: **Configure** on the integration card (default 30 s).

## How detection works

The integration reads `Device/IP/Interfaces` and follows each interface's `LowerLayers` chain down
to the physical layer:

```
IP_DATA   > PPP_DATA > VLAN_DATA > GPON_DATA > OPTICAL0   -> fiber
IP_BACKUP > LTE_MODEM                                     -> mobile
```

- fiber data interface `UP` and GPON state `OPERATIONAL` → **fiber**
- otherwise mobile interface `UP` → **mobile**
- both down → **offline**

VoIP, IPTV, management and LAN interfaces are ignored.

## Example automations

```yaml
automation:
  - alias: Internet switched to LTE backup
    triggers:
      - trigger: state
        entity_id: sensor.sagemcom_f_st_192_168_1_1_connection_type
        to: mobile
        for: "00:01:00"
    actions:
      - action: notify.notify
        data:
          message: Internet switched to LTE backup

  - alias: Weak fiber signal
    triggers:
      - trigger: numeric_state
        entity_id: sensor.sagemcom_f_st_192_168_1_1_optical_rx_power
        below: -27
        for: "00:10:00"
    actions:
      - action: notify.notify
        data:
          message: "Fiber RX power is low: {{ trigger.to_state.state }} dBm"
```

Check the actual entity IDs on the device page.

## Reporting another router model

Use **Settings → Devices → Sagemcom F@st → ⋮ → Download diagnostics** and attach the file to an issue.
Public IPs, IPv6 prefixes, MAC addresses, serial numbers and PPPoE credentials are removed, but
please check the file before posting.

Without Home Assistant: `pip install sagemcom_api` and `python tools/probe.py 192.168.1.1 admin "PASSWORD"`.
The probe dump is **not** anonymized.

## Notes

- The router allows a limited number of sessions. Being logged in to the web UI at the same time
  can cause temporary login errors. If the web GUI is inaccessible, stop/disable this integration,
  wait about one minute, log in, then re-enable the integration.
- Uses [python-sagemcom-api](https://github.com/iMicknl/python-sagemcom-api).
  Not affiliated with Sagemcom or Deutsche Telekom.

## License

MIT
