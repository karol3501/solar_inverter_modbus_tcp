from __future__ import annotations

import logging
import time

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SolarInverterCoordinator

_LOGGER = logging.getLogger(__name__)


def _device_info() -> DeviceInfo:
    return DeviceInfo(identifiers={(DOMAIN, "solar_inverter")}, name="Solar Inverter", manufacturer="Generic", model="Modbus TCP")


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SolarInverterCoordinator = entry.runtime_data
    async_add_entities([
        PeakShavingNumber(coordinator, "peak_meter_baseline_soc", "Peak Shaving Baseline SOC", 10, 100, 1, True),
        PeakShavingNumber(coordinator, "peak_meter_reserved_soc", "Peak Shaving Reserved SOC", 10, 100, 1, False),
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
        self._attr_device_info = _device_info()

    @property
    def extra_state_attributes(self):
        return {
            "modbus_function": "FC06",
            "modbus_address": "4446",
            "modbus_registers": "4446-4446",
            "modbus_role": "high byte" if self._high_byte else "low byte",
        }

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.get(self._data_key)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        requested = max(10, min(100, int(value)))

        async with self.coordinator.modbus_lock:
            started = time.monotonic()

            # Use the latest coordinator value so both controls operate on the
            # same packed register without an unnecessary FC03 request.
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

            # Optimistic update: reflect the user's change immediately.
            # The next coordinator poll confirms the actual inverter value.
            updated = dict(self.coordinator.data)
            updated["r4446"] = raw
            updated["peak_meter_baseline_soc"] = raw // 256
            updated["peak_meter_reserved_soc"] = raw % 256
            self.coordinator.async_set_updated_data(updated)
            self.async_write_ha_state()

            if self.coordinator.debug_logging:
                _LOGGER.debug("MODBUS WRITE | FC06 | address=4446 | value=%s", raw)

            try:
                await self.coordinator.unit.write_register(4446, raw)
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("PEAK SHAVING WRITE FAILED | FC06 | address=4446 | value=%s | duration=%.3fs | error=%s", raw, time.monotonic() - started, err)
                raise

            if self.coordinator.debug_logging:
                _LOGGER.debug("MODBUS WRITE SUCCESS | FC06 | address=4446 | duration=%.3fs", time.monotonic() - started)
