from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from modbus_connection import ModbusTcpParams

from .const import CONF_UNIT_ID, DEFAULT_PORT, DEFAULT_UNIT_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SolarInverterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            try:
                unit_id = int(user_input[CONF_UNIT_ID])
            except ValueError:
                unit_id = -1

            if not 1 <= unit_id <= 247:
                errors[CONF_UNIT_ID] = "invalid_unit_id"
            else:
                try:
                    params = ModbusTcpParams(host=host, port=port)
                    async with async_get_temporary_unit(self.hass, params, unit_id) as unit:
                        result = await unit.read_holding_registers(4300, 1)
                        if not result:
                            raise RuntimeError("empty response")
                except Exception:
                    errors["base"] = "cannot_connect"
                    _LOGGER.exception("Modbus FC03 register 4300 failed")
                else:
                    await self.async_set_unique_id(f"{host}:{port}:{unit_id}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Solar Inverter ({host})",
                        data={CONF_HOST: host, CONF_PORT: port, CONF_UNIT_ID: unit_id},
                    )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
                vol.Required(CONF_UNIT_ID, default=str(DEFAULT_UNIT_ID)): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
