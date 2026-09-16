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
from .device import ev_charger_device_info, inverter_device_info

_LOGGER = logging.getLogger(__name__)
_INTER_REQUEST_DELAY = 0.25


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SolarInverterCoordinator = entry.runtime_data
    entities = [
        PeakShavingNumber(coordinator, "peak_meter_baseline_soc", "Peak Shaving Baseline SOC", 10, 100, 1, True),
        PeakShavingNumber(coordinator, "peak_meter_reserved_soc", "Peak Shaving Reserved SOC", 10, 100, 1, False),
        ExportPowerLimitNumber(coordinator),
        BatterySettingNumber(
            coordinator,
            "battery_maximum_charge_power",
            "Battery Maximum Charge Power",
            306,
            0,
            100,
            0.1,
        ),
        BatterySettingNumber(
            coordinator,
            "battery_maximum_discharge_power",
            "Battery Maximum Discharge Power",
            307,
            0,
            100,
            0.1,
        ),
        BatterySettingNumber(
            coordinator,
            "battery_maximum_soc",
            "Battery Maximum SOC",
            308,
            70,
            100,
        ),
        BatterySettingNumber(
            coordinator,
            "battery_minimum_soc",
            "Battery Minimum SOC",
            309,
            10,
            50,
        ),
    ]
    ems_settings = [
        ("ems_self_use_reserved_soc", "Self-Use Reserved SOC", 4301, 10, 100, 1.0, "%", NumberMode.SLIDER),
        ("ems_backup_reserved_soc", "Backup Reserved SOC", 4302, 60, 100, 1.0, "%", NumberMode.SLIDER),
        ("ems_force_charge_soc", "Force Charge SOC", 4303, 10, 100, 1.0, "%", NumberMode.SLIDER),
        ("ems_force_charge_maximum_power", "Force Charge Maximum Power", 4304, 0, 100, 0.1, "%", NumberMode.SLIDER),
        ("ems_force_discharge_soc", "Force Discharge SOC", 4305, 10, 100, 1.0, "%", NumberMode.SLIDER),
        ("ems_force_discharge_maximum_power", "Force Discharge Maximum Power", 4306, 0, 100, 0.1, "%", NumberMode.SLIDER),
        ("tou_period_1_charge_start_hour", "TOU Period 1 Charge Start Hour", 4449, 0, 23, 1.0, None, NumberMode.BOX),
        ("tou_period_1_charge_start_minute", "TOU Period 1 Charge Start Minute", 4450, 0, 59, 1.0, None, NumberMode.BOX),
        ("tou_period_1_charge_end_hour", "TOU Period 1 Charge End Hour", 4451, 0, 23, 1.0, None, NumberMode.BOX),
        ("tou_period_1_charge_end_minute", "TOU Period 1 Charge End Minute", 4452, 0, 59, 1.0, None, NumberMode.BOX),
        ("tou_period_1_charge_power", "TOU Period 1 Charge Power", 4453, 0, 100, 1.0, "%", NumberMode.SLIDER),
        ("tou_period_1_stop_charge_soc", "TOU Period 1 Stop Charge SOC", 4454, 10, 100, 1.0, "%", NumberMode.SLIDER),
        ("tou_period_1_discharge_start_hour", "TOU Period 1 Discharge Start Hour", 4455, 0, 23, 1.0, None, NumberMode.BOX),
        ("tou_period_1_discharge_start_minute", "TOU Period 1 Discharge Start Minute", 4456, 0, 59, 1.0, None, NumberMode.BOX),
        ("tou_period_1_discharge_end_hour", "TOU Period 1 Discharge End Hour", 4457, 0, 23, 1.0, None, NumberMode.BOX),
        ("tou_period_1_discharge_end_minute", "TOU Period 1 Discharge End Minute", 4458, 0, 59, 1.0, None, NumberMode.BOX),
        ("tou_period_1_discharge_power", "TOU Period 1 Discharge Power", 4459, 0, 100, 1.0, "%", NumberMode.SLIDER),
        ("tou_period_1_stop_discharge_soc", "TOU Period 1 Stop Discharge SOC", 4460, 10, 100, 1.0, "%", NumberMode.SLIDER),
    ]
    entities.extend(EmsSettingNumber(coordinator, *setting) for setting in ems_settings)
    for charger in coordinator.ev_chargers or ():
        address = 4700 if charger == 1 else 4750
        rated_power_kw = coordinator.ev_charger_rated_power_kw[charger]
        entities.extend(
            (
                EvChargerPowerNumber(
                    coordinator,
                    charger,
                    "charging_power_setting",
                    "Charging Power Setting",
                    address,
                    rated_power_kw,
                ),
                EvChargerPowerNumber(
                    coordinator,
                    charger,
                    "offline_charging_power",
                    "Offline Charging Power",
                    address + 1,
                    rated_power_kw,
                ),
                EvChargerPowerNumber(
                    coordinator,
                    charger,
                    "max_charging_power_from_grid",
                    "Max Charging Power from Grid",
                    address + 4,
                    rated_power_kw,
                ),
            )
        )
    async_add_entities(entities)


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
    _attr_mode = NumberMode.SLIDER
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
    _attr_mode = NumberMode.SLIDER
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
        scale: float = 1.0,
    ) -> None:
        super().__init__(coordinator)
        self._data_key = data_key
        self._address = address
        self._scale = scale
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_{data_key}"
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_device_info = inverter_device_info(coordinator)

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.get(f"r{self._address}")
        return float(value) * self._scale if value is not None else None

    @property
    def extra_state_attributes(self):
        raw_value = self.coordinator.data.get(f"r{self._address}")
        return {
            "modbus_address": self._address,
            "raw_value": int(raw_value) if raw_value is not None else None,
        }

    async def async_set_native_value(self, value: float) -> None:
        requested = max(
            self._attr_native_min_value,
            min(self._attr_native_max_value, round(value)),
        )
        raw_value = round(requested / self._scale)

        async with self.coordinator.modbus_lock:
            started = time.monotonic()
            if self.coordinator.debug_logging:
                _LOGGER.debug(
                    "MODBUS WRITE | FC06 | address=%s | value=%s",
                    self._address,
                    raw_value,
                )
            try:
                await self.coordinator.unit.write_register(self._address, raw_value)
                await asyncio.sleep(_INTER_REQUEST_DELAY)
                values = await self.coordinator.unit.read_holding_registers(
                    self._address, 1
                )
                if not values or int(values[0]) != raw_value:
                    raise RuntimeError(
                        "Battery setting write verification failed: "
                        f"expected {raw_value}, got {values!r}"
                    )
            except Exception as err:
                _LOGGER.error(
                    "BATTERY SETTING WRITE FAILED | FC06 | address=%s | value=%s | "
                    "duration=%.3fs | error=%s",
                    self._address,
                    raw_value,
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


class EmsSettingNumber(CoordinatorEntity[SolarInverterCoordinator], NumberEntity):
    """Expose one verified EMS holding-register setting."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_step = 1

    def __init__(self, coordinator, data_key, name, address, minimum, maximum, scale, unit, mode) -> None:
        super().__init__(coordinator)
        self._address = address
        self._scale = scale
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_{data_key}"
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_unit_of_measurement = unit
        self._attr_mode = mode
        self._attr_device_info = inverter_device_info(coordinator)

    @property
    def native_value(self):
        value = self.coordinator.data.get(f"r{self._address}")
        return float(value) * self._scale if value is not None else None

    @property
    def extra_state_attributes(self):
        raw = self.coordinator.data.get(f"r{self._address}")
        return {"modbus_address": self._address, "raw_value": int(raw) if raw is not None else None}

    async def async_set_native_value(self, value: float) -> None:
        requested = max(
            self._attr_native_min_value,
            min(self._attr_native_max_value, float(value)),
        )
        raw = round(requested / self._scale)
        async with self.coordinator.modbus_lock:
            await self.coordinator.unit.write_register(self._address, raw)
            await asyncio.sleep(_INTER_REQUEST_DELAY)
            values = await self.coordinator.unit.read_holding_registers(self._address, 1)
            if not values or int(values[0]) != raw:
                raise RuntimeError(f"EMS setting write verification failed: expected {raw}, got {values!r}")
        updated = dict(self.coordinator.data)
        updated[f"r{self._address}"] = int(values[0])
        self.coordinator.async_set_updated_data(updated)


class EvChargerPowerNumber(EmsSettingNumber):
    """Expose one verified EV charger power setting in kW."""

    _attr_native_unit_of_measurement = "kW"
    _attr_mode = NumberMode.SLIDER
    _attr_native_step = 0.1

    def __init__(
        self,
        coordinator: SolarInverterCoordinator,
        charger: int,
        data_key: str,
        name: str,
        address: int,
        rated_power_kw: float,
    ) -> None:
        super().__init__(
            coordinator,
            f"ev_charger_{charger}_{data_key}",
            name,
            address,
            0,
            rated_power_kw,
            0.1,
            "kW",
            NumberMode.SLIDER,
        )
        self._attr_device_info = ev_charger_device_info(coordinator, charger)

