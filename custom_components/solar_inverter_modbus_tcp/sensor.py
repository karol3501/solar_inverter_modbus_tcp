from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, EMS_MODES
from .coordinator import SolarInverterCoordinator

DESCRIPTION = SensorEntityDescription(key="ems_mode", name="EMS Mode (4300)")


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SolarInverterCoordinator = entry.runtime_data
    async_add_entities([SolarInverterSensor(coordinator, DESCRIPTION)])


class SolarInverterSensor(CoordinatorEntity[SolarInverterCoordinator], SensorEntity):
    def __init__(self, coordinator: SolarInverterCoordinator, description: SensorEntityDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "solar_inverter")},
            "name": "Solar Inverter",
            "manufacturer": "Generic",
            "model": "Modbus TCP",
        }

    @property
    def native_value(self) -> str | None:
        value = self.coordinator.data.get("ems_mode")
        if value is None:
            return None
        return EMS_MODES.get(int(value), f"Unknown ({value})")
