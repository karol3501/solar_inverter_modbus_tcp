from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from modbus_connection import ModbusTcpParams

from .const import (
    CONF_DEBUG_LOGGING,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class SolarInverterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            try:
                unit_id = int(user_input[CONF_UNIT_ID])
            except (TypeError, ValueError):
                unit_id = -1

            if not host:
                errors[CONF_HOST] = "invalid_host"
            elif not 1 <= port <= 65535:
                errors[CONF_PORT] = "invalid_port"
            elif not 1 <= unit_id <= 247:
                errors[CONF_UNIT_ID] = "invalid_unit_id"
            else:
                try:
                    params = ModbusTcpParams(host=host, port=port)
                    async with async_get_temporary_unit(self.hass, params, unit_id) as unit:
                        result = await unit.read_holding_registers(4300, 1)
                        if not result:
                            raise RuntimeError("empty response")
                except Exception as err:  # noqa: BLE001
                    errors["base"] = "cannot_connect"
                    _LOGGER.warning(
                        "Unable to validate Modbus connection to %s:%s: %s",
                        host,
                        port,
                        err,
                    )
                else:
                    await self.async_set_unique_id(f"{host}:{port}:{unit_id}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Solar Inverter ({host})",
                        data={
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_UNIT_ID: unit_id,
                        },
                        options={
                            CONF_SCAN_INTERVAL: 10,
                            CONF_DEBUG_LOGGING: bool(
                                user_input.get(CONF_DEBUG_LOGGING, False)
                            ),
                        },
                    )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
                vol.Required(
                    CONF_UNIT_ID, default=str(DEFAULT_UNIT_ID)
                ): str,
                vol.Optional(CONF_DEBUG_LOGGING, default=False): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(self, user_input=None) -> FlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            try:
                unit_id = int(user_input[CONF_UNIT_ID])
            except (TypeError, ValueError):
                unit_id = -1

            if not host:
                errors[CONF_HOST] = "invalid_host"
            elif not 1 <= port <= 65535:
                errors[CONF_PORT] = "invalid_port"
            elif not 1 <= unit_id <= 247:
                errors[CONF_UNIT_ID] = "invalid_unit_id"
            else:
                try:
                    params = ModbusTcpParams(host=host, port=port)
                    async with async_get_temporary_unit(self.hass, params, unit_id) as unit:
                        result = await unit.read_holding_registers(4300, 1)
                        if not result:
                            raise RuntimeError("empty response")
                except Exception as err:  # noqa: BLE001
                    errors["base"] = "cannot_connect"
                    _LOGGER.warning(
                        "Unable to validate reconfigured Modbus connection to %s:%s: %s",
                        host,
                        port,
                        err,
                    )
                else:
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_UNIT_ID: unit_id,
                        },
                    )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=entry.data.get(CONF_HOST, ""),
                ): str,
                vol.Required(
                    CONF_PORT,
                    default=entry.data.get(CONF_PORT, DEFAULT_PORT),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                vol.Required(
                    CONF_UNIT_ID,
                    default=str(entry.data.get(CONF_UNIT_ID, DEFAULT_UNIT_ID)),
                ): str,
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return SolarInverterOptionsFlow(config_entry)


class SolarInverterOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DEBUG_LOGGING,
                    default=self.config_entry.options.get(CONF_DEBUG_LOGGING, False),
                ): bool,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(CONF_SCAN_INTERVAL, 10),
                ): vol.All(vol.Coerce(int), vol.Range(min=2, max=3600)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
