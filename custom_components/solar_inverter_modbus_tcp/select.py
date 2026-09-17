from __future__ import annotations

import asyncio
import logging
import time

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, EMS_MODES
from .coordinator import SolarInverterCoordinator
from .device import ev_charger_device_info, inverter_device_info

_LOGGER = logging.getLogger(__name__)
OPTIONS = list(EMS_MODES.values())
NAME_TO_VALUE = {name: value for value, name in EMS_MODES.items()}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SolarInverterCoordinator = entry.runtime_data
    entities = [SolarInverterEmsSelect(coordinator)]
    for charger in coordinator.ev_chargers or ():
        address = 4700 if charger == 1 else 4750
        entities.extend(
            (
                EvChargerSettingSelect(
                    coordinator,
                    charger,
                    "charging_mode",
                    "Charging Mode",
                    address + 2,
                    {"Plug and Charge": 1, "RFID Authentication": 2},
                ),
                EvChargerSettingSelect(
                    coordinator,
                    charger,
                    "green_power_mode",
                    "Green Power Mode",
                    address + 3,
                    {"Disable": 0, "Enable": 1},
                ),
            )
        )
    async_add_entities(entities)


class SolarInverterEmsSelect(CoordinatorEntity[SolarInverterCoordinator], SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "EMS Mode Control"
    _attr_options = OPTIONS

    def __init__(self, coordinator: SolarInverterCoordinator) -> None:
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_ems_mode_control"
        self._attr_device_info = inverter_device_info(coordinator)

    @property
    def extra_state_attributes(self):
        return {"modbus_address": "4300"}

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


class EvChargerSettingSelect(
    CoordinatorEntity[SolarInverterCoordinator], SelectEntity
):
    """Expose one verified EV charger selection setting."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: SolarInverterCoordinator,
        charger: int,
        data_key: str,
        name: str,
        address: int,
        option_to_value: dict[str, int],
    ) -> None:
        super().__init__(coordinator)
        self._address = address
        self._option_to_value = option_to_value
        self._value_to_option = {
            value: option for option, value in option_to_value.items()
        }
        self._attr_name = name
        self._attr_options = list(option_to_value)
        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.entry_id}_ev_charger_{charger}_{data_key}"
        )
        self._attr_device_info = ev_charger_device_info(coordinator, charger)

    @property
    def extra_state_attributes(self):
        value = self.coordinator.data.get(f"r{self._address}")
        return {
            "modbus_address": str(self._address),
            "raw_value": int(value) if value is not None else None,
        }

    @property
    def current_option(self) -> str | None:
        value = self.coordinator.data.get(f"r{self._address}")
        return self._value_to_option.get(int(value)) if value is not None else None

    async def async_select_option(self, option: str) -> None:
        value = self._option_to_value[option]
        async with self.coordinator.modbus_lock:
            started = time.monotonic()
            if self.coordinator.debug_logging:
                _LOGGER.debug(
                    "MODBUS WRITE | FC06 | address=%s | value=%s",
                    self._address,
                    value,
                )
            await self.coordinator.unit.write_register(self._address, value)
            await asyncio.sleep(0.25)
            values = await self.coordinator.unit.read_holding_registers(
                self._address, 1
            )
            if not values or int(values[0]) != value:
                raise RuntimeError(
                    "EV charger setting write verification failed: "
                    f"expected {value}, got {values!r}"
                )

        updated = dict(self.coordinator.data)
        updated[f"r{self._address}"] = int(values[0])
        self.coordinator.async_set_updated_data(updated)
        if self.coordinator.debug_logging:
            _LOGGER.debug(
                "MODBUS WRITE SUCCESS | FC06 | address=%s | duration=%.3fs",
                self._address,
                time.monotonic() - started,
            )

