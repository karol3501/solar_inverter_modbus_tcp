from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusUnit

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SolarInverterCoordinator(DataUpdateCoordinator[dict[str, object]]):
    """Minimal diagnostic: FC03 holding register 4300."""

    def __init__(self, hass: HomeAssistant, unit: ModbusUnit, update_interval: int = 10) -> None:
        self.unit = unit
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> dict[str, object]:
        try:
            values = await self.unit.read_holding_registers(4300, 1)
            if not values:
                raise UpdateFailed("FC03 register 4300 returned no data")
            _LOGGER.debug("Modbus FC03 4300 response: %s", values)
            return {"ems_mode": values[0]}
        except Exception as err:
            _LOGGER.exception("Modbus FC03 4300 read failed: %s", err)
            raise UpdateFailed(
                f"FC03 register 4300 failed: {type(err).__name__}: {err}"
            ) from err
