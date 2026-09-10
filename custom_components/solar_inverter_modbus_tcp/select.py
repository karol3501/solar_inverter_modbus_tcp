from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, EMS_MODES
from .coordinator import SolarInverterCoordinator

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
    def current_option(self) -> str | None:
        value = self.coordinator.data.get("ems_mode")
        if value is None:
            return None
        return EMS_MODES.get(int(value))

    async def async_select_option(self, option: str) -> None:
        value = NAME_TO_VALUE[option]

        # Some inverter firmware does not respond to FC06 for EMS register 4300.
        # Use FC16 for the complete EMS settings block (4300-4306), preserving
        # the current values of the other settings.
        settings = await self.coordinator.unit.read_holding_registers(4300, 7)
        if len(settings) != 7:
            raise RuntimeError(
                f"EMS settings read returned {len(settings)} registers, expected 7"
            )

        settings[0] = value
        await self.coordinator.unit.write_registers(4300, settings)

        values = await self.coordinator.unit.read_holding_registers(4300, 1)
        if not values or int(values[0]) != value:
            raise RuntimeError(
                f"EMS mode write verification failed: expected {value}, got {values!r}"
            )

        updated = dict(self.coordinator.data)
        updated["ems_mode"] = int(values[0])
        self.coordinator.async_set_updated_data(updated)
