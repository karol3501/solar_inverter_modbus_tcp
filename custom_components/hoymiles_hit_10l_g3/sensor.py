from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, EMS_MODES
from .coordinator import HoymilesCoordinator

DESCRIPTION = SensorEntityDescription(key="ems_mode", name="EMS Mode Test (4300)")


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: HoymilesCoordinator = entry.runtime_data
    async_add_entities([HoymilesSensor(coordinator, DESCRIPTION)])


class HoymilesSensor(CoordinatorEntity[HoymilesCoordinator], SensorEntity):
    def __init__(
        self, coordinator: HoymilesCoordinator, description: SensorEntityDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "hoymiles_hit_g3")},
            "name": "Hoymiles HIT-10L-G3",
            "manufacturer": "Hoymiles",
            "model": "HIT-10L-G3",
        }

    @property
    def native_value(self):
        value = self.coordinator.data.get("ems_mode")
        if value is None:
            return None
        return EMS_MODES.get(int(value), f"Unknown ({value})")
