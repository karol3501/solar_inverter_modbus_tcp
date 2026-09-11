from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusUnit

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_READ_RETRIES = 2
_RETRY_DELAY = 0.5


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

    def __init__(
        self,
        hass: HomeAssistant,
        unit: ModbusUnit,
        entry_id: str,
        update_interval: int = 10,
        debug_logging: bool = False,
    ) -> None:
        self.unit = unit
        self.entry_id = entry_id
        self.debug_logging = debug_logging
        self.modbus_lock = asyncio.Lock()
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=update_interval))

    def _debug(self, message: str, *args: object) -> None:
        if self.debug_logging:
            _LOGGER.debug(message, *args)

    async def _read(self, function: str, address: int, count: int) -> list[int]:
        last_error: Exception | None = None
        end = address + count - 1
        reader = self.unit.read_input_registers if function == "FC04" else self.unit.read_holding_registers
        for attempt in range(1, _READ_RETRIES + 1):
            started = time.monotonic()
            self._debug(
                "MODBUS READ | %s | address=%s | count=%s | range=%s-%s | attempt=%s/%s",
                function, address, count, address, end, attempt, _READ_RETRIES,
            )
            try:
                values = await reader(address, count)
                if len(values) != count:
                    raise UpdateFailed(
                        f"{function} read {address}-{end} returned {len(values)} registers, expected {count}"
                    )
                result = [int(value) for value in values]
                self._debug(
                    "MODBUS RESPONSE | %s | range=%s-%s | registers=%s | duration=%.3fs | values=%s",
                    function, address, end, len(result), time.monotonic() - started, result,
                )
                return result
            except Exception as err:  # noqa: BLE001
                last_error = err
                duration = time.monotonic() - started
                if attempt < _READ_RETRIES:
                    _LOGGER.warning(
                        "MODBUS READ RETRY | %s | address=%s | count=%s | range=%s-%s | attempt=%s/%s | duration=%.3fs | error=%s",
                        function, address, count, address, end, attempt, _READ_RETRIES, duration, err,
                    )
                    await asyncio.sleep(_RETRY_DELAY)
                else:
                    _LOGGER.error(
                        "MODBUS READ FAILED | %s | address=%s | count=%s | range=%s-%s | attempts=%s | duration=%.3fs | error=%s",
                        function, address, count, address, end, _READ_RETRIES, duration, err,
                    )
        assert last_error is not None
        raise last_error

    async def _read_input(self, address: int, count: int) -> list[int]:
        return await self._read("FC04", address, count)

    async def _read_holding(self, address: int, count: int) -> list[int]:
        return await self._read("FC03", address, count)

    async def _async_update_data(self) -> dict[str, object]:
        async with self.modbus_lock:
            started = time.monotonic()
            try:
                data = await self._async_update_data_locked()
            except Exception:
                _LOGGER.exception("MODBUS UPDATE FAILED | entry_id=%s", self.entry_id)
                raise
            self._debug("MODBUS UPDATE SUCCESS | requests=16 | duration=%.3fs", time.monotonic() - started)
            return data

    async def _async_update_data_locked(self) -> dict[str, object]:
        try:
            input_blocks = [
                (0, 39), (45, 36), (81, 14), (113, 3), (201, 1), (210, 1), (241, 3),
                (1022, 4), (1046, 1), (1060, 1), (1078, 18), (2000, 70), (2100, 36),
            ]
            data: dict[str, object] = {}
            for address, count in input_blocks:
                _put_block(data, await self._read_input(address, count), address)

            for address, count in ((259, 1), (4300, 8), (4446, 2)):
                _put_block(data, await self._read_holding(address, count), address)

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
            _LOGGER.exception("Modbus telemetry read failed")
            raise UpdateFailed(f"Modbus telemetry read failed: {type(err).__name__}: {err}") from err
