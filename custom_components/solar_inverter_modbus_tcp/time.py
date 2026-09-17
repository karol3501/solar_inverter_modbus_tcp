"""Time controls for the solar inverter integration."""

from __future__ import annotations

import asyncio
from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SolarInverterCoordinator
from .device import inverter_device_info

_INTER_REQUEST_DELAY = 0.25

_TOU_TIME_SETTINGS = (
    ("tou_period_1_charge_start_time", "TOU Period 1 Charge Start Time", 4449),
    ("tou_period_1_charge_end_time", "TOU Period 1 Charge End Time", 4451),
    ("tou_period_1_discharge_start_time", "TOU Period 1 Discharge Start Time", 4455),
    ("tou_period_1_discharge_end_time", "TOU Period 1 Discharge End Time", 4457),
)


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SolarInverterCoordinator = entry.runtime_data
    async_add_entities(
        TouPeriodTime(coordinator, data_key, name, address)
        for data_key, name, address in _TOU_TIME_SETTINGS
    )


class TouPeriodTime(CoordinatorEntity[SolarInverterCoordinator], TimeEntity):
    """Expose one verified TOU start or end time."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: SolarInverterCoordinator,
        data_key: str,
        name: str,
        address: int,
    ) -> None:
        super().__init__(coordinator)
        self._address = address
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_{data_key}"
        self._attr_device_info = inverter_device_info(coordinator)

    @property
    def native_value(self) -> time | None:
        hour = self.coordinator.data.get(f"r{self._address}")
        minute = self.coordinator.data.get(f"r{self._address + 1}")
        if hour is None or minute is None:
            return None
        return time(int(hour), int(minute))

    @property
    def extra_state_attributes(self):
        return {
            "modbus_address_hour": str(self._address),
            "modbus_address_minute": str(self._address + 1),
        }

    async def async_set_value(self, value: time) -> None:
        registers = [value.hour, value.minute]
        async with self.coordinator.modbus_lock:
            await self.coordinator.unit.write_registers(self._address, registers)
            await asyncio.sleep(_INTER_REQUEST_DELAY)
            values = await self.coordinator.unit.read_holding_registers(
                self._address, 2
            )
            if [int(item) for item in values] != registers:
                raise RuntimeError(
                    "TOU time write verification failed: "
                    f"expected {registers}, got {values!r}"
                )

        updated = dict(self.coordinator.data)
        updated[f"r{self._address}"] = int(values[0])
        updated[f"r{self._address + 1}"] = int(values[1])
        self.coordinator.async_set_updated_data(updated)

