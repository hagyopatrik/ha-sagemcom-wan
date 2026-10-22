# Sagemcom F@st WAN Monitor

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![Validate](https://github.com/hagyopatrik/ha-sagemcom-wan/actions/workflows/validate.yml/badge.svg)](https://github.com/hagyopatrik/ha-sagemcom-wan/actions/workflows/validate.yml)

Home Assistant integration that shows whether a **Sagemcom F@st** router is currently
connected through **fiber (GPON)** or its **LTE mobile backup**.

Built and tested on the **Sagemcom F@st 5670** (Telekom Hungary). Other F@st models that
use the `/cgi/json-req` API and the TR-181 data model should work as well.

## Features

- UI setup (config flow), authentication method detected automatically (MD5 / MD5_NONCE / SHA512)
- `Connection type` sensor: `fiber`, `mobile`, `offline`, `unknown`
- Attributes: `on_mobile`, `interface`, `chain`, `fiber_status`, `mobile_status`, `gpon_state`
- Configurable polling interval (default 30 s)
- Diagnostics download for reporting unsupported models

## Installation

### HACS (recommended)

1. HACS → three dots menu → **Custom repositories**
2. Repository: `https://github.com/hagyopatrik/ha-sagemcom-wan`, Type: **Integration**
3. Install **Sagemcom F@st WAN Monitor** and restart Home Assistant

### Manual

Copy `custom_components/sagemcom_wan` to `/config/custom_components/` and restart Home Assistant.

## Configuration

**Settings → Devices & services → Add integration → Sagemcom F@st WAN Monitor**

| Field | F@st 5670 (Telekom HU) |
|---|---|
| Host | `192.168.1.1` |
| Username | `admin` |
| Password | router admin password |
| Use HTTPS | off |

Polling interval: **Configure** on the integration card.

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

## Example automation

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
```

## Reporting another router model

1. `pip install sagemcom_api`
2. `python tools/probe.py 192.168.1.1 admin "PASSWORD"`
3. Open an issue with the output and `sagemcom_dump.json` (remove public IPs and serial numbers),
   or attach **Download diagnostics** from the device page.

## Notes

- The router allows a limited number of sessions. Being logged in to the web UI at the same time
  can cause temporary login errors.
- Uses [python-sagemcom-api](https://github.com/iMicknl/python-sagemcom-api).
  Not affiliated with Sagemcom or Deutsche Telekom.

## License

MIT
