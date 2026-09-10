from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusUnit

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _i16(value: int) -> int:
    value = int(value)
    return value - 0x10000 if value & 0x8000 else value


def _i32(hi: int, lo: int) -> int:
    raw = (int(hi) << 16) | int(lo)
    return raw - 0x100000000 if raw & 0x80000000 else raw


def _put_block(data: dict[str, object], values: list[int], start: int) -> None:
    for offset, value in enumerate(values):
        data[f"r{start + offset}"] = int(value)


class SolarInverterCoordinator(DataUpdateCoordinator[dict[str, object]]):
    """Poll all telemetry used by the original Modbus YAML configuration."""

    def __init__(self, hass: HomeAssistant, unit: ModbusUnit, entry_id: str, update_interval: int = 10) -> None:
        self.unit = unit
        self.entry_id = entry_id
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=update_interval))

    async def _read_input(self, address: int, count: int) -> list[int]:
        values = await self.unit.read_input_registers(address, count)
        if len(values) != count:
            raise UpdateFailed(f"FC04 read {address}-{address + count - 1} returned {len(values)} registers, expected {count}")
        return [int(value) for value in values]

    async def _read_holding(self, address: int, count: int) -> list[int]:
        values = await self.unit.read_holding_registers(address, count)
        if len(values) != count:
            raise UpdateFailed(f"FC03 read {address}-{address + count - 1} returned {len(values)} registers, expected {count}")
        return [int(value) for value in values]

    async def _async_update_data(self) -> dict[str, object]:
        try:
            input_blocks = [
                (0, 39), (45, 50), (113, 3), (201, 1), (210, 1), (241, 3),
                (1022, 4), (1046, 1), (1060, 1), (1078, 18), (2000, 70), (2100, 36),
            ]
            data: dict[str, object] = {}
            for address, count in input_blocks:
                _put_block(data, await self._read_input(address, count), address)

            for address, count in ((259, 1), (4300, 8), (4446, 2)):
                _put_block(data, await self._read_holding(address, count), address)

            # 32-bit values.
            data["sw_fault"] = _i32(data["r19"], data["r20"])
            data["r48"] = _i32(data["r48"], data["r49"])
            data["r50"] = _i32(data["r50"], data["r51"])

            for address in (1078, 1080, 1082, 1084, 1086, 1088, 1090, 1092, 1094):
                data[f"r{address}"] = _i32(data[f"r{address}"], data[f"r{address + 1}"])

            for address in (2000, 2022, 2024, 2026, 2028, 2030, 2040, 2048, 2056, 2064, 2066, 2068):
                data[f"r{address}"] = _i32(data[f"r{address}"], data[f"r{address + 1}"])

            data["work_status_text"] = {
                0: "PowerInit", 1: "StdbyMode", 2: "GridOnTest", 3: "PowerInit",
                4: "FaultMode", 5: "GridOffMode", 6: "ByPassMode", 7: "PVChargeBat",
                8: "GenMode", 9: "IPSMode",
            }.get(int(data["r0"]), "Unknown")
            data["total_pv_power"] = sum(int(data[f"r{x}"]) for x in (29, 32, 35, 38))
            data["total_grid_power"] = -sum(int(data[f"r{x}"]) for x in (1078, 1080, 1082))
            data["total_inverter_power"] = sum(_i16(int(data[f"r{x}"])) for x in (74, 75, 76))
            data["load_power"] = abs(abs(int(data["total_inverter_power"])) - abs(int(data["total_grid_power"])))
            data["ems_mode"] = int(data["r4300"])
            data["peak_meter_baseline_soc"] = int(data["r4446"]) // 256
            data["peak_meter_reserved_soc"] = int(data["r4446"]) % 256
            return data
        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.exception("Modbus telemetry read failed: %s", err)
            raise UpdateFailed(f"Modbus telemetry read failed: {type(err).__name__}: {err}") from err
