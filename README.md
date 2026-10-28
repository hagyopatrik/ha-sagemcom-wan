<div align="center">

# Sagemcom F@st WAN Monitor

**Know at a glance whether your internet runs on fiber or LTE backup.**

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square)](https://hacs.xyz)
[![Validate](https://img.shields.io/github/actions/workflow/status/hagyopatrik/ha-sagemcom-wan/validate.yml?style=flat-square&label=validate)](https://github.com/hagyopatrik/ha-sagemcom-wan/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/hagyopatrik/ha-sagemcom-wan?style=flat-square)](https://github.com/hagyopatrik/ha-sagemcom-wan/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](LICENSE)

</div>

---

A Home Assistant integration for **Sagemcom F@st** routers. It shows the active WAN connection
(fiber or mobile backup) and adds sensors for optical signal, traffic and WAN status.

## ✅ Tested device

| Router | Provider | Status |
|---|---|---|
| **Sagemcom F@st 5670** | Magyar Telekom (Hungary) | Works perfectly |

Other F@st models probably work too, if they use the same web API. See [Compatibility](#-compatibility).

> [!IMPORTANT]
> **Stop the integration before you log in to the router's web interface.**
>
> The router allows only a few sessions at the same time. If the integration is running,
> the web login fails with a *maximum number of connections* error.
>
> 1. **Settings → Devices & services → Sagemcom F@st WAN Monitor → ⋮ → Disable**
> 2. Wait about **1 minute**.
> 3. Log in to the web interface. It works normally.
> 4. When you are done, log out and **Enable** the integration again.

## ✨ Features

- **Connection type:** `fiber`, `mobile`, `offline` or `unknown`
- **Optical signal:** RX / TX power in dBm
- **Traffic:** current download / upload rate and daily usage for fiber and LTE
- **WAN info:** public IPv4, connection uptime, last error
- **LTE backup:** modem status
- UI setup, login method detected automatically
- Sensors are only created if your router provides the data

## 📦 Installation

### HACS

1. Open **HACS → ⋮ → Custom repositories**
2. Add `https://github.com/hagyopatrik/ha-sagemcom-wan` with type **Integration**
3. Install **Sagemcom F@st WAN Monitor**
4. Restart Home Assistant

### Manual

Copy `custom_components/sagemcom_wan` into your `/config/custom_components/` folder and restart Home Assistant.

## ⚙️ Setup

**Settings → Devices & services → Add integration → Sagemcom F@st WAN Monitor**

| Field | Value |
|---|---|
| Host | `192.168.1.1` |
| Username | `admin` |
| Password | your router admin password |
| Use HTTPS | off |

You can change the polling interval under **Configure** (default: 30 seconds).

## 📊 Sensors

| Sensor | Example |
|---|---|
| Connection type | `fiber` |
| Optical RX / TX power | `-25.85 dBm` / `3.32 dBm` |
| Download / upload rate | `48.2 Mbit/s` |
| Fiber / mobile usage today | `11.8 GB` |
| Public IPv4 address | `203.0.113.10` |
| Fiber connected since | timestamp |
| LTE modem status | `DORMANT` |

Diagnostic sensors (module temperature, voltage, laser bias, GPON state, alarms) are available on the device page.

<details>
<summary><b>How does fiber / mobile detection work?</b></summary>

<br>

The integration follows each WAN interface down to the physical layer:

```
IP_DATA   → PPP_DATA → VLAN_DATA → GPON_DATA → OPTICAL0   = fiber
IP_BACKUP → LTE_MODEM                                     = mobile
```

- Fiber interface is up and GPON is `OPERATIONAL` → **fiber**
- Otherwise, LTE interface is up → **mobile**
- Neither is up → **offline**

</details>

<details>
<summary><b>Example automation: notify on LTE failover</b></summary>

<br>

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

Check your actual entity ID on the device page.

</details>

## 🤝 Compatibility

**Tested it on another router? Please let me know!**

Open an [issue](https://github.com/hagyopatrik/ha-sagemcom-wan/issues/new?title=Compatibility%3A%20) and include:

- Router model and provider
- Whether it worked (fully, partly, not at all)
- Optional: **Device page → ⋮ → Download diagnostics** (personal data is removed, but please check the file before posting)

Every report helps to grow the compatibility list.

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| *Maximum number of connections* in the web interface | Disable the integration, wait 1 minute, then log in |
| *Too many open sessions* during setup | Log out of the web interface, wait 1 minute, try again |
| *Invalid username or password* | Check the admin password on the router's label |
| A sensor is missing | Your router does not provide that value |

## 📄 License

[MIT](LICENSE) · Built on [python-sagemcom-api](https://github.com/iMicknl/python-sagemcom-api) · Not affiliated with Sagemcom or Magyar Telekom.
