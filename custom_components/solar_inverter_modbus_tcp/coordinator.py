from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusUnit

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _i32(values: list[int], index: int) -> int:
    """Decode two consecutive Modbus registers as signed big-endian I32."""
    raw = (int(values[index]) << 16) | int(values[index + 1])
    return raw - 0x100000000 if raw & 0x80000000 else raw


def _put_block(data: dict[str, object], values: list[int], start: int, addresses: list[int]) -> None:
    """Copy selected U16/I16 values from a contiguous Modbus block."""
    for address in addresses:
        data[f"r{address}"] = int(values[address - start])


class SolarInverterCoordinator(DataUpdateCoordinator[dict[str, object]]):
    """Poll basic inverter telemetry using efficient contiguous Modbus blocks."""

    def __init__(
        self,
        hass: HomeAssistant,
        unit: ModbusUnit,
        entry_id: str,
        update_interval: int = 10,
    ) -> None:
        self.unit = unit
        self.entry_id = entry_id
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _read(self, address: int, count: int) -> list[int]:
        values = await self.unit.read_input_registers(address, count)
        if len(values) != count:
            raise UpdateFailed(
                f"FC04 read {address}-{address + count - 1} returned "
                f"{len(values)} registers, expected {count}"
            )
        return [int(value) for value in values]

    async def _async_update_data(self) -> dict[str, object]:
        try:
            ems = await self.unit.read_holding_registers(4300, 1)
            if not ems:
                raise UpdateFailed("FC03 register 4300 returned no data")

            pv = await self._read(26, 13)       # 26-38
            battery = await self._read(45, 7)   # 45-51
            ac = await self._read(58, 37)       # 58-94

            # The meter I32 registers are sparse and end at 1095 because
            # register 1094 is the high word of the final I32 value.
            ac_meter = await self._read(1078, 18)  # 1078-1095

            data: dict[str, object] = {"ems_mode": int(ems[0])}

            _put_block(
                data,
                pv,
                26,
                [26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38],
            )
            _put_block(data, battery, 45, [45, 46, 48, 50])
            _put_block(
                data,
                ac,
                58,
                [
                    58, 59, 60,
                    62, 63, 64, 66,
                    67, 68, 69, 70, 71, 72,
                    73, 74, 75, 76,
                    77, 78, 79, 80,
                    81, 82, 83, 84, 85, 86,
                    87, 88, 89, 90,
                    91, 92, 93, 94,
                ],
            )

            # The YAML configuration uses scale: -1 for grid active power.
            data["r1078"] = -_i32(ac_meter, 0)
            data["r1080"] = -_i32(ac_meter, 2)
            data["r1082"] = -_i32(ac_meter, 4)
            data["r1084"] = _i32(ac_meter, 6)
            data["r1086"] = _i32(ac_meter, 8)
            data["r1088"] = _i32(ac_meter, 10)
            data["r1090"] = _i32(ac_meter, 12)
            data["r1092"] = _i32(ac_meter, 14)
            data["r1094"] = _i32(ac_meter, 16)

            # Battery current and power are I32 on G3-compatible models.
            data["battery_current"] = _i32(battery, 3)
            data["battery_power"] = _i32(battery, 5)

            _LOGGER.debug("Modbus telemetry update: %s", data)
            return data
        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.exception("Modbus telemetry read failed: %s", err)
            raise UpdateFailed(
                f"Modbus telemetry read failed: {type(err).__name__}: {err}"
            ) from err
