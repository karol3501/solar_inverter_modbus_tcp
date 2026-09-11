from __future__ import annotations

import logging

from homeassistant.components.modbus import async_get_unit
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from modbus_connection import ModbusTcpParams

from .const import CONF_DEBUG_LOGGING, CONF_SCAN_INTERVAL, CONF_UNIT_ID
from .coordinator import SolarInverterCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "select", "number"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    params = ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT])
    unit = async_get_unit(hass, entry, params, entry.data[CONF_UNIT_ID])
    coordinator = SolarInverterCoordinator(
        hass,
        unit,
        entry.entry_id,
        update_interval=entry.options.get(CONF_SCAN_INTERVAL, 10),
        debug_logging=entry.options.get(CONF_DEBUG_LOGGING, False),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    from . import debug_attributes, sensor
    debug_attributes.patch_sensor_entities(sensor)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
