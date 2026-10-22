"""Constants for the Sagemcom F@st WAN integration."""
from __future__ import annotations

DOMAIN = "sagemcom_wan"

CONF_ENCRYPTION_METHOD = "encryption_method"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_USERNAME = "admin"
DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 3600

ENCRYPTION_AUTO = "auto"
