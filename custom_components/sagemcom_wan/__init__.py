"""The Sagemcom F@st WAN integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .client import create_client
from .coordinator import SagemcomWanCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type SagemcomWanConfigEntry = ConfigEntry[SagemcomWanCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SagemcomWanConfigEntry) -> bool:
    """Set up from a config entry."""
    client = create_client(hass, dict(entry.data))
    coordinator = SagemcomWanCoordinator(hass, entry, client)
    await coordinator.async_fetch_device_info()
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SagemcomWanConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_shutdown()
    return unloaded


async def _async_reload(hass: HomeAssistant, entry: SagemcomWanConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
