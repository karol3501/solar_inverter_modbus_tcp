from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, EMS_MODES
from .coordinator import SolarInverterCoordinator

_LOGGER = logging.getLogger(__name__)
OPTIONS = list(EMS_MODES.values())
NAME_TO_VALUE = {name: value for value, name in EMS_MODES.items()}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SolarInverterCoordinator = entry.runtime_data
    async_add_entities([SolarInverterEmsSelect(coordinator)])


class SolarInverterEmsSelect(CoordinatorEntity[SolarInverterCoordinator], SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "EMS Mode Control"
    _attr_options = OPTIONS

    def __init__(self, coordinator: SolarInverterCoordinator) -> None:
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_ems_mode_control"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "solar_inverter")},
            "name": "Solar Inverter",
            "manufacturer": "Generic",
            "model": "Modbus TCP",
        }

    @property
    def extra_state_attributes(self):
        return {
            "modbus_function": "FC16",
            "modbus_address": "4300",
            "modbus_registers": "4300-4306",
            "modbus_verify": "FC03 address=4300",
        }

    @property
    def current_option(self) -> str | None:
        value = self.coordinator.data.get("ems_mode")
        if value is None:
            return None
        return EMS_MODES.get(int(value))

    async def async_select_option(self, option: str) -> None:
        value = NAME_TO_VALUE[option]
        async with self.coordinator.modbus_lock:
            started = __import__("time").monotonic()
            if self.coordinator.debug_logging:
                _LOGGER.debug("MODBUS WRITE | FC03 | address=4300 | count=7 | range=4300-4306")
            settings = await self.coordinator.unit.read_holding_registers(4300, 7)
            if len(settings) != 7:
                raise RuntimeError(f"EMS settings read returned {len(settings)} registers, expected 7")

            settings[0] = value
            if self.coordinator.debug_logging:
                _LOGGER.debug("MODBUS WRITE | FC16 | address=4300 | count=7 | range=4300-4306 | values=%s", settings)
            await self.coordinator.unit.write_registers(4300, settings)

            if self.coordinator.debug_logging:
                _LOGGER.debug("MODBUS VERIFY | FC03 | address=4300 | count=1")
            values = await self.coordinator.unit.read_holding_registers(4300, 1)
            if not values or int(values[0]) != value:
                raise RuntimeError(f"EMS mode write verification failed: expected {value}, got {values!r}")
            if self.coordinator.debug_logging:
                _LOGGER.debug("MODBUS WRITE SUCCESS | FC16 | range=4300-4306 | duration=%.3fs", __import__("time").monotonic() - started)

        updated = dict(self.coordinator.data)
        updated["ems_mode"] = int(values[0])
        self.coordinator.async_set_updated_data(updated)
