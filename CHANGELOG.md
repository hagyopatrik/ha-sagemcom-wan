# Changelog

## 1.1.0
- New sensors (created only when the router exposes the data):
  - Optical RX / TX power (dBm), module temperature, voltage, laser bias current, optical alarm, GPON state
  - Download / upload rate (Mbit/s) from the WAN counters
  - Fiber and mobile (LTE) download / upload today
  - Public IPv4 address, fiber connected since, WAN last connection error
  - LTE modem status and raw RSSI
- Device model and firmware read from the G.988 (OMCI) section when `Device/DeviceInfo` is not available
- Diagnostics: no extra router requests, and much stricter redaction (public IPs, IPv6 prefixes,
  PPPoE peer MAC and encrypted PPPoE credentials are removed)
- Hungarian translation
- Unit tests with the F@st 5670AXv2 data layout

## 1.0.1
- Login: SHA512 tried first, fresh client per attempt, retry on login throttling

## 1.0.0
- First release
