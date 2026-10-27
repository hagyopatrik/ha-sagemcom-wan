"""Sensors for the Sagemcom F@st WAN integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_HOST,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfDataRate,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfInformation,
    UnitOfTemperature,
)
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


@dataclass(frozen=True, kw_only=True)
class MetricDescription(SensorEntityDescription):
    """Sensor reading one key of coordinator.data['metrics']."""

    # create the entity when this metric exists, even if its own value is None
    # (e.g. rates on the first poll, public IP while on mobile backup)
    depends_on: str | None = None


def _bytes(key: str, **kw: Any) -> MetricDescription:
    return MetricDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=2,
        **kw,
    )


def _rate(key: str) -> MetricDescription:
    return MetricDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        suggested_display_precision=1,
        depends_on="fiber_download_today",
    )


METRICS: tuple[MetricDescription, ...] = (
    MetricDescription(
        key="optical_rx_power",
        translation_key="optical_rx_power",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        suggested_display_precision=2,
        icon="mdi:sine-wave",
    ),
    MetricDescription(
        key="optical_tx_power",
        translation_key="optical_tx_power",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        suggested_display_precision=2,
        icon="mdi:sine-wave",
    ),
    MetricDescription(
        key="optical_temperature",
        translation_key="optical_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MetricDescription(
        key="optical_voltage",
        translation_key="optical_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    MetricDescription(
        key="optical_bias_current",
        translation_key="optical_bias_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    MetricDescription(
        key="optical_alarm",
        translation_key="optical_alarm",
        icon="mdi:alert-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MetricDescription(
        key="gpon_state",
        translation_key="gpon_state",
        icon="mdi:access-point-network",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    _rate("download_rate"),
    _rate("upload_rate"),
    _bytes("fiber_download_today", icon="mdi:download"),
    _bytes("fiber_upload_today", icon="mdi:upload"),
    _bytes("mobile_download_today", icon="mdi:download-network"),
    _bytes("mobile_upload_today", icon="mdi:upload-network"),
    MetricDescription(
        key="public_ipv4",
        translation_key="public_ipv4",
        icon="mdi:ip-network",
        depends_on="fiber_last_change",
    ),
    MetricDescription(
        key="fiber_connected_since",
        translation_key="fiber_connected_since",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-start",
        depends_on="fiber_last_change",
    ),
    MetricDescription(
        key="wan_last_error",
        translation_key="wan_last_error",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        depends_on="fiber_last_change",
    ),
    MetricDescription(
        key="lte_modem_status",
        translation_key="lte_modem_status",
        icon="mdi:sim",
    ),
    MetricDescription(
        key="lte_rssi",
        translation_key="lte_rssi",
        icon="mdi:signal",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SagemcomWanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    metrics = (coordinator.data or {}).get("metrics", {})
    entities: list[SensorEntity] = [WanTypeSensor(coordinator, entry)]
    for desc in METRICS:
        anchor = desc.depends_on or desc.key
        if metrics.get(anchor) is not None:
            entities.append(MetricSensor(coordinator, entry, desc))
    async_add_entities(entities)


class _Base(CoordinatorEntity[SagemcomWanCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: SagemcomWanCoordinator, entry: SagemcomWanConfigEntry) -> None:
        super().__init__(coordinator)
        info = coordinator.device_info_raw
        host = entry.data[CONF_HOST]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="Sagemcom",
            model=info.get("model") or "F@st",
            sw_version=info.get("sw_version"),
            hw_version=info.get("hw_version"),
            name=f"Sagemcom F@st ({host})",
            configuration_url=f"http://{host}",
        )


class WanTypeSensor(_Base):
    """Reports fiber / mobile / offline / unknown."""

    _attr_translation_key = "connection_type"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATES

    def __init__(self, coordinator: SagemcomWanCoordinator, entry: SagemcomWanConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_connection_type"

    @property
    def _det(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get("detection", {})

    @property
    def native_value(self) -> str | None:
        return self._det.get("connection")

    @property
    def icon(self) -> str:
        return ICONS.get(self.native_value or "unknown", "mdi:help-network")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = dict(self._det)
        data.pop("connection", None)
        data["on_mobile"] = self.native_value == STATE_MOBILE
        return data


class MetricSensor(_Base):
    """Generic metric sensor."""

    entity_description: MetricDescription

    def __init__(
        self,
        coordinator: SagemcomWanCoordinator,
        entry: SagemcomWanConfigEntry,
        description: MetricDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        return (self.coordinator.data or {}).get("metrics", {}).get(self.entity_description.key)
