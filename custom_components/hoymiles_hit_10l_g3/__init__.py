from __future__ import annotations

from homeassistant.components.modbus import async_get_unit
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from modbus_connection import ModbusTcpParams

from .const import CONF_SCAN_INTERVAL, CONF_UNIT_ID, DOMAIN
from .coordinator import HoymilesCoordinator

PLATFORMS = ["sensor", "select"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    params = ModbusTcpParams(
        host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]
    )
    unit = async_get_unit(hass, entry, params, entry.data[CONF_UNIT_ID])
    coordinator = HoymilesCoordinator(
        hass, unit, update_interval=entry.options.get(CONF_SCAN_INTERVAL, 10)
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
