from __future__ import annotations

import asyncio
import logging
import time

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfPower
from homeassistant.helpers.entity import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SolarInverterCoordinator
from .device import inverter_device_info

_LOGGER = logging.getLogger(__name__)
_INTER_REQUEST_DELAY = 0.25


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SolarInverterCoordinator = entry.runtime_data
    async_add_entities([
        PeakShavingNumber(coordinator, "peak_meter_baseline_soc", "Peak Shaving Baseline SOC", 10, 100, 1, True),
        PeakShavingNumber(coordinator, "peak_meter_reserved_soc", "Peak Shaving Reserved SOC", 10, 100, 1, False),
        ExportPowerLimitNumber(coordinator),
        BatterySettingNumber(
            coordinator,
            "battery_maximum_charge_power",
            "Battery Maximum Charge Power",
            306,
            10,
            100,
        ),
        BatterySettingNumber(
            coordinator,
            "battery_maximum_discharge_power",
            "Battery Maximum Discharge Power",
            307,
            10,
            100,
        ),
        BatterySettingNumber(
            coordinator,
            "battery_maximum_soc",
            "Battery Maximum SOC",
            308,
            10,
            100,
        ),
        BatterySettingNumber(
            coordinator,
            "battery_minimum_soc",
            "Battery Minimum SOC",
            309,
            10,
            90,
        ),
    ])


class PeakShavingNumber(CoordinatorEntity[SolarInverterCoordinator], NumberEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "%"
    _attr_device_class = None
    _attr_mode = NumberMode.AUTO

    def __init__(self, coordinator: SolarInverterCoordinator, data_key: str, name: str, minimum: float, maximum: float, step: float, high_byte: bool) -> None:
        super().__init__(coordinator)
        self._data_key = data_key
        self._high_byte = high_byte
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_{data_key}"
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_device_info = inverter_device_info(coordinator)

    @property
    def extra_state_attributes(self):
        return {
            "modbus_address": 4446,
            "modbus_role": "high byte" if self._high_byte else "low byte",
        }

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.get(self._data_key)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        requested = max(10, min(100, int(value)))

        async with self.coordinator.modbus_lock:
            await asyncio.sleep(_INTER_REQUEST_DELAY)
            started = time.monotonic()
            current_value = self.coordinator.data.get("r4446")
            if current_value is None:
                current = await self.coordinator.unit.read_holding_registers(4446, 1)
                if not current:
                    raise RuntimeError("FC03 register 4446 returned no data")
                current_value = int(current[0])

            current_raw = int(current_value)
            if self._high_byte:
                raw = (requested << 8) | (current_raw & 0xFF)
            else:
                raw = (current_raw & 0xFF00) | requested

            if self.coordinator.debug_logging:
                _LOGGER.debug("MODBUS WRITE | FC06 | address=4446 | value=%s", raw)

            try:
                await self.coordinator.unit.write_register(4446, raw)
                await asyncio.sleep(_INTER_REQUEST_DELAY)
            except Exception as err:
                _LOGGER.error("PEAK SHAVING WRITE FAILED | FC06 | address=4446 | value=%s | duration=%.3fs | error=%s", raw, time.monotonic() - started, err)
                try:
                    await self.coordinator.unit.disconnect()
                except Exception as disconnect_err:  # noqa: BLE001
                    _LOGGER.debug("MODBUS DISCONNECT FAILED AFTER PEAK SHAVING WRITE | error=%s", disconnect_err)
                raise

            updated = dict(self.coordinator.data)
            updated["r4446"] = raw
            updated["peak_meter_baseline_soc"] = raw // 256
            updated["peak_meter_reserved_soc"] = raw % 256
            self.coordinator.async_set_updated_data(updated)

            if self.coordinator.debug_logging:
                _LOGGER.debug("MODBUS WRITE SUCCESS | FC06 | address=4446 | duration=%.3fs", time.monotonic() - started)


class ExportPowerLimitNumber(CoordinatorEntity[SolarInverterCoordinator], NumberEntity):
    """Expose the percentage-based GCF export limit as watts."""

    _attr_has_entity_name = True
    _attr_name = "Export Power Limit"
    _attr_device_class = NumberDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_mode = NumberMode.BOX
    _attr_native_step = 1
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: SolarInverterCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_export_power_limit"
        self._attr_native_min_value = 0
        self._attr_native_max_value = coordinator.export_limit_watts
        self._attr_device_info = inverter_device_info(coordinator)

    @property
    def native_value(self) -> float | None:
        raw_value = self.coordinator.data.get("r259")
        if raw_value is None:
            return None
        return round(int(raw_value) * self.coordinator.inverter_rated_power_watts / 1000)

    @property
    def extra_state_attributes(self):
        raw_value = self.coordinator.data.get("r259")
        return {
            "modbus_address": 259,
            "raw_value": int(raw_value) if raw_value is not None else None,
            "percent": int(raw_value) / 10 if raw_value is not None else None,
            "inverter_rated_power_watts": self.coordinator.inverter_rated_power_watts,
            "configured_export_limit_watts": self.coordinator.export_limit_watts,
        }

    async def async_set_native_value(self, value: float) -> None:
        requested = max(0, min(self.coordinator.export_limit_watts, round(value)))
        raw_value = round(
            requested * 1000 / self.coordinator.inverter_rated_power_watts
        )

        async with self.coordinator.modbus_lock:
            started = time.monotonic()
            if self.coordinator.debug_logging:
                _LOGGER.debug(
                    "MODBUS WRITE | FC06 | address=259 | value=%s | watts=%s",
                    raw_value,
                    requested,
                )
            await self.coordinator.unit.write_register(259, raw_value)
            await asyncio.sleep(_INTER_REQUEST_DELAY)
            values = await self.coordinator.unit.read_holding_registers(259, 1)
            if not values or int(values[0]) != raw_value:
                raise RuntimeError(
                    "Export limit write verification failed: "
                    f"expected {raw_value}, got {values!r}"
                )

        updated = dict(self.coordinator.data)
        updated["r259"] = int(values[0])
        self.coordinator.async_set_updated_data(updated)
        if self.coordinator.debug_logging:
            _LOGGER.debug(
                "MODBUS WRITE SUCCESS | FC06 | address=259 | duration=%.3fs",
                time.monotonic() - started,
            )


class BatterySettingNumber(CoordinatorEntity[SolarInverterCoordinator], NumberEntity):
    """Control a documented percentage-based battery setting."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "%"
    _attr_mode = NumberMode.AUTO
    _attr_native_step = 1
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: SolarInverterCoordinator,
        data_key: str,
        name: str,
        address: int,
        minimum: int,
        maximum: int,
    ) -> None:
        super().__init__(coordinator)
        self._data_key = data_key
        self._address = address
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_{data_key}"
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_device_info = inverter_device_info(coordinator)

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.get(f"r{self._address}")
        return float(value) if value is not None else None

    @property
    def extra_state_attributes(self):
        return {"modbus_address": self._address}

    async def async_set_native_value(self, value: float) -> None:
        requested = max(
            self._attr_native_min_value,
            min(self._attr_native_max_value, round(value)),
        )

        async with self.coordinator.modbus_lock:
            started = time.monotonic()
            if self.coordinator.debug_logging:
                _LOGGER.debug(
                    "MODBUS WRITE | FC06 | address=%s | value=%s",
                    self._address,
                    requested,
                )
            try:
                await self.coordinator.unit.write_register(self._address, requested)
                await asyncio.sleep(_INTER_REQUEST_DELAY)
                values = await self.coordinator.unit.read_holding_registers(
                    self._address, 1
                )
                if not values or int(values[0]) != requested:
                    raise RuntimeError(
                        "Battery setting write verification failed: "
                        f"expected {requested}, got {values!r}"
                    )
            except Exception as err:
                _LOGGER.error(
                    "BATTERY SETTING WRITE FAILED | FC06 | address=%s | value=%s | "
                    "duration=%.3fs | error=%s",
                    self._address,
                    requested,
                    time.monotonic() - started,
                    err,
                )
                try:
                    await self.coordinator.unit.disconnect()
                except Exception as disconnect_err:  # noqa: BLE001
                    _LOGGER.debug(
                        "MODBUS DISCONNECT FAILED AFTER BATTERY SETTING WRITE | error=%s",
                        disconnect_err,
                    )
                raise

        updated = dict(self.coordinator.data)
        updated[f"r{self._address}"] = int(values[0])
        self.coordinator.async_set_updated_data(updated)
        if self.coordinator.debug_logging:
            _LOGGER.debug(
                "MODBUS WRITE SUCCESS | FC06 | address=%s | duration=%.3fs",
                self._address,
                time.monotonic() - started,
            )
