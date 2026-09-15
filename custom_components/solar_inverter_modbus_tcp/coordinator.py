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
_INTER_REQUEST_DELAY = 0.25


def _i16(value: int) -> int:
    value = int(value)
    return value - 0x10000 if value & 0x8000 else value


def _i32(hi: int, lo: int) -> int:
    raw = (int(hi) << 16) | int(lo)
    return raw - 0x100000000 if raw & 0x80000000 else raw


def _u32(hi: int, lo: int) -> int:
    return (int(hi) << 16) | int(lo)


def _u64(w0: int, w1: int, w2: int, w3: int) -> int:
    return (
        (int(w0) << 48)
        | (int(w1) << 32)
        | (int(w2) << 16)
        | int(w3)
    )


def _put_block(data: dict[str, object], values: list[int], start: int) -> None:
    for offset, value in enumerate(values):
        data[f"r{start + offset}"] = int(value)


def _is_connection_error(error: Exception) -> bool:
    text = str(error).lower()
    return "timeout" in text or "connection lost" in text or "connection" in text


class SolarInverterCoordinator(DataUpdateCoordinator[dict[str, object]]):
    """Poll telemetry used by the Modbus integration."""

    def __init__(
        self,
        hass: HomeAssistant,
        unit: ModbusUnit,
        entry_id: str,
        update_interval: int = 10,
        debug_logging: bool = False,
        enable_generator: bool = False,
        enable_ev_charger: bool = False,
        ev_chargers: list[int] | tuple[int, ...] | None = None,
    ) -> None:
        self.unit = unit
        self.entry_id = entry_id
        self.debug_logging = debug_logging
        self.enable_generator = enable_generator
        self.enable_ev_charger = enable_ev_charger
        self.ev_chargers = None if ev_chargers is None else tuple(int(charger) for charger in ev_chargers)
        self.modbus_lock = asyncio.Lock()
        self._last_data: dict[str, object] = {}
        self._successful_requests = 0
        self._failed_requests = 0
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
            self._debug("MODBUS READ | %s | address=%s | count=%s | range=%s-%s | attempt=%s/%s", function, address, count, address, end, attempt, _READ_RETRIES)
            try:
                values = await reader(address, count)
                if len(values) != count:
                    raise UpdateFailed(f"{function} read {address}-{end} returned {len(values)} registers, expected {count}")
                result = [int(value) for value in values]
                self._debug("MODBUS RESPONSE | %s | range=%s-%s | registers=%s | duration=%.3fs | values=%s", function, address, end, len(result), time.monotonic() - started, result)
                await asyncio.sleep(_INTER_REQUEST_DELAY)
                return result
            except Exception as err:  # noqa: BLE001
                last_error = err
                duration = time.monotonic() - started
                if _is_connection_error(err):
                    try:
                        await self.unit.disconnect()
                    except Exception as disconnect_err:  # noqa: BLE001
                        _LOGGER.debug("MODBUS DISCONNECT FAILED | error=%s", disconnect_err)
                if attempt < _READ_RETRIES:
                    _LOGGER.warning("MODBUS READ RETRY | %s | address=%s | count=%s | range=%s-%s | attempt=%s/%s | duration=%.3fs | error=%s", function, address, count, address, end, attempt, _READ_RETRIES, duration, err)
                    await asyncio.sleep(_RETRY_DELAY)
                else:
                    _LOGGER.error("MODBUS READ FAILED | %s | address=%s | count=%s | range=%s-%s | attempts=%s | duration=%.3fs | error=%s", function, address, count, address, end, _READ_RETRIES, duration, err)
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
            self._last_data = data.copy()
            self._debug("MODBUS UPDATE SUCCESS | successful=%s | failed=%s | duration=%.3fs", self._successful_requests, self._failed_requests, time.monotonic() - started)
            return data

    async def _async_update_data_locked(self) -> dict[str, object]:
        input_blocks = [
            (0, 39), (45, 7), (62, 15), (81, 3), (91, 4), (113, 3),
            (201, 1), (1022, 4), (1046, 4), (1060, 1), (1078, 6),
            (2000, 69), (2100, 36),
        ]
        if self.enable_generator:
            input_blocks.append((103, 9))

        if self.enable_ev_charger:
            if self.ev_chargers is None:
                for charger, address in ((1, 3200), (2, 3250)):
                    try:
                        values = await self._read_input(address, 1)
                        _put_block(self._last_data, values, address)
                    except Exception as err:  # noqa: BLE001
                        _LOGGER.warning("EV CHARGER DETECTION FAILED | charger=%s | address=%s | error=%s", charger, address, err)
                detected = []
                for charger, base_address in ((1, 3200), (2, 3250)):
                    serial_words = [
                        self._last_data.get(f"r{base_address + offset}")
                        for offset in range(2, 6)
                    ]
                    if (
                        int(self._last_data.get(f"r{base_address}", 0)) == 1
                        and 1
                        <= int(self._last_data.get(f"r{base_address + 1}", 0))
                        <= 247
                        and all(word is not None for word in serial_words)
                        and any(int(word) != 0 for word in serial_words)
                    ):
                        detected.append(charger)
                self.ev_chargers = tuple(detected)
                _LOGGER.info("EV CHARGER DETECTION | detected=%s", list(self.ev_chargers))
            for charger in self.ev_chargers:
                if charger == 1:
                    input_blocks.append((3200, 25))
                elif charger == 2:
                    input_blocks.append((3250, 25))

        holding_blocks = [(259, 1), (4300, 8), (4446, 2)]
        total_requests = len(input_blocks) + len(holding_blocks)
        data: dict[str, object] = self._last_data.copy()
        self._successful_requests = 0
        self._failed_requests = 0

        connection_failed = False
        for function, blocks in (("FC04", input_blocks), ("FC03", holding_blocks)):
            for address, count in blocks:
                try:
                    values = await (self._read_input(address, count) if function == "FC04" else self._read_holding(address, count))
                    _put_block(data, values, address)
                    self._successful_requests += 1
                except Exception as err:  # noqa: BLE001
                    self._failed_requests += 1
                    connection_failed = _is_connection_error(err)
                    _LOGGER.warning("MODBUS BLOCK SKIPPED | %s | address=%s | range=%s-%s | using last good data | error=%s", function, address, address, address + count - 1, err)
                    if connection_failed:
                        _LOGGER.warning("MODBUS CONNECTION RECOVERY | stopping current poll after failed %s request; next poll will reconnect", function)
                        break
            if connection_failed:
                break

        if self._successful_requests == 0:
            raise UpdateFailed(f"Modbus telemetry update failed: all {total_requests} requests failed")

        if "r21" in data and "r22" in data:
            data["r21"] = _u32(data["r21"], data["r22"])

        for key, high_key, low_key in (
            ("sw_fault", "r19", "r20"),
            *((f"r{x}", f"r{x}", f"r{x + 1}") for x in (48, 50)),
            *((f"r{x}", f"r{x}", f"r{x + 1}") for x in (1078, 1080, 1082)),
            *((f"r{x}", f"r{x}", f"r{x + 1}") for x in (2000, 2022, 2024, 2026, 2028, 2030, 2040, 2048, 2056, 2064, 2066, 2068)),
        ):
            if high_key in data and low_key in data:
                data[key] = _i32(data[high_key], data[low_key])

        if all(f"r{x}" in data for x in (29, 32, 35, 38)):
            data["total_pv_power"] = sum(int(data[f"r{x}"]) for x in (29, 32, 35, 38))
        if all(f"r{x}" in data for x in (74, 75, 76)):
            data["total_inverter_power"] = sum(_i16(int(data[f"r{x}"])) for x in (74, 75, 76))
        if all(f"r{x}" in data for x in (92, 93, 94)):
            data["backup_active_power"] = sum(_i16(int(data[f"r{x}"])) for x in (92, 93, 94))
        if all(f"r{x}" in data for x in (1078, 1080, 1082)):
            data["total_grid_power"] = -sum(int(data[f"r{x}"]) for x in (1078, 1080, 1082))
        if "total_inverter_power" in data and "total_grid_power" in data:
            data["load_power"] = abs(int(data["total_inverter_power"]) + int(data["total_grid_power"]))
        if "r0" in data:
            data["work_status_text"] = {0: "Initialising", 1: "Standby", 2: "Grid Check", 3: "Initialising", 4: "Fault", 5: "Grid Off", 6: "Bypass", 7: "PV Charging Battery", 8: "Generator Mode", 9: "Island Mode"}.get(int(data["r0"]), f"Unknown ({int(data['r0'])})")
        if "r4300" in data:
            data["ems_mode"] = int(data["r4300"])
        if "r4446" in data:
            data["peak_meter_baseline_soc"] = int(data["r4446"]) // 256
            data["peak_meter_reserved_soc"] = int(data["r4446"]) % 256

        return data

