"""WAN connection type sensor."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SagemcomWanConfigEntry
from .const import DOMAIN
from .coordinator import SagemcomWanCoordinator
from .wan_detect import STATE_MOBILE, STATES

ICONS = {
    "fiber": "mdi:wan",
    "mobile": "mdi:signal-4g",
    "offline": "mdi:lan-disconnect",
    "unknown": "mdi:help-network",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SagemcomWanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([WanTypeSensor(entry.runtime_data, entry)])


class WanTypeSensor(CoordinatorEntity[SagemcomWanCoordinator], SensorEntity):
    """Reports fiber / mobile / offline / unknown."""

    _attr_has_entity_name = True
    _attr_translation_key = "connection_type"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATES

    def __init__(self, coordinator: SagemcomWanCoordinator, entry: SagemcomWanConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_connection_type"
        info = coordinator.device_info_raw
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="Sagemcom",
            model=info.get("model") or "F@st",
            sw_version=info.get("sw_version"),
            hw_version=info.get("hw_version"),
            serial_number=info.get("serial"),
            name=f"Sagemcom F@st ({entry.data[CONF_HOST]})",
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("connection") if self.coordinator.data else None

    @property
    def icon(self) -> str:
        return ICONS.get(self.native_value or "unknown", "mdi:help-network")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = dict(self.coordinator.data or {})
        data.pop("connection", None)
        data["on_mobile"] = self.native_value == STATE_MOBILE
        return data
