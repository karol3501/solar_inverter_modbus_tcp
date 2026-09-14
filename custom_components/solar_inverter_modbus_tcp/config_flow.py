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
    CONF_ENABLE_EV_CHARGER,
    CONF_ENABLE_GENERATOR,
    CONF_EV_CHARGERS,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class SolarInverterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _detect_ev_chargers(self, host: str, port: int, unit_id: int) -> list[int]:
        params = ModbusTcpParams(host=host, port=port)
        detected: list[int] = []
        async with async_get_temporary_unit(self.hass, params, unit_id) as unit:
            for charger, base_address in ((1, 3200), (2, 3250)):
                try:
                    status = await unit.read_input_registers(base_address, 1)
                    address = await unit.read_input_registers(base_address + 1, 1)
                    serial = await unit.read_input_registers(base_address + 2, 4)
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug(
                        "EV charger %s is not available at Modbus block %s: %s",
                        charger,
                        base_address,
                        err,
                    )
                    continue

                if (
                    status
                    and int(status[0]) == 1
                    and address
                    and 1 <= int(address[0]) <= 247
                    and serial
                    and any(int(value) != 0 for value in serial)
                ):
                    detected.append(charger)
        return detected

    def _ev_detection_placeholders(self, chargers: list[int]) -> dict[str, str]:
        if not chargers:
            detected = "No EV charger detected"
        else:
            detected = ", ".join(f"EV Charger {charger}" for charger in chargers)
        return {"detected_ev_chargers": detected}

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
                    options = {
                        CONF_SCAN_INTERVAL: int(user_input.get(CONF_SCAN_INTERVAL, 10)),
                        CONF_DEBUG_LOGGING: bool(user_input.get(CONF_DEBUG_LOGGING, False)),
                        CONF_ENABLE_GENERATOR: bool(user_input.get(CONF_ENABLE_GENERATOR, False)),
                        CONF_ENABLE_EV_CHARGER: bool(user_input.get(CONF_ENABLE_EV_CHARGER, False)),
                        CONF_EV_CHARGERS: [],
                    }
                    if options[CONF_ENABLE_EV_CHARGER]:
                        try:
                            detected = await self._detect_ev_chargers(host, port, unit_id)
                        except Exception as err:  # noqa: BLE001
                            _LOGGER.warning("Unable to detect EV chargers: %s", err)
                            errors["base"] = "ev_detection_failed"
                        else:
                            self._pending_entry_options = options
                            self._pending_entry_data = {
                                CONF_HOST: host,
                                CONF_PORT: port,
                                CONF_UNIT_ID: unit_id,
                            }
                            self._pending_ev_chargers = detected
                            self._pending_reconfigure = False
                            return self.async_show_form(
                                step_id="ev_detection",
                                data_schema=vol.Schema({}),
                                description_placeholders=self._ev_detection_placeholders(detected),
                            )
                    if not errors:
                        return self.async_create_entry(
                            title=f"Solar Inverter ({host})",
                            data={
                                CONF_HOST: host,
                                CONF_PORT: port,
                                CONF_UNIT_ID: unit_id,
                            },
                            options=options,
                        )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                vol.Required(CONF_UNIT_ID, default=str(DEFAULT_UNIT_ID)): str,
                vol.Optional(CONF_DEBUG_LOGGING, default=False): bool,
                vol.Optional(CONF_SCAN_INTERVAL, default=10): vol.All(vol.Coerce(int), vol.Range(min=2, max=3600)),
                vol.Optional(CONF_ENABLE_GENERATOR, default=False): bool,
                vol.Optional(CONF_ENABLE_EV_CHARGER, default=False): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_ev_detection(self, user_input=None) -> FlowResult:
        options = self._pending_entry_options
        options[CONF_EV_CHARGERS] = self._pending_ev_chargers
        if self._pending_reconfigure:
            return self.async_update_reload_and_abort(
                self._pending_reconfigure_entry,
                data_updates=self._pending_entry_data,
                options_updates=options,
            )
        return self.async_create_entry(
            title=f"Solar Inverter ({self._pending_entry_data[CONF_HOST]})",
            data=self._pending_entry_data,
            options=options,
        )

    async def async_step_reconfigure(self, user_input=None) -> FlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        current_options = entry.options

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
                    options = {
                        CONF_SCAN_INTERVAL: int(user_input.get(CONF_SCAN_INTERVAL, current_options.get(CONF_SCAN_INTERVAL, 10))),
                        CONF_DEBUG_LOGGING: bool(user_input.get(CONF_DEBUG_LOGGING, current_options.get(CONF_DEBUG_LOGGING, False))),
                        CONF_ENABLE_GENERATOR: bool(user_input.get(CONF_ENABLE_GENERATOR, current_options.get(CONF_ENABLE_GENERATOR, False))),
                        CONF_ENABLE_EV_CHARGER: bool(user_input.get(CONF_ENABLE_EV_CHARGER, current_options.get(CONF_ENABLE_EV_CHARGER, False))),
                        CONF_EV_CHARGERS: [],
                    }
                    data_updates = {
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_UNIT_ID: unit_id,
                    }
                    if options[CONF_ENABLE_EV_CHARGER]:
                        try:
                            detected = await self._detect_ev_chargers(host, port, unit_id)
                        except Exception as err:  # noqa: BLE001
                            _LOGGER.warning("Unable to detect EV chargers during reconfigure: %s", err)
                            errors["base"] = "ev_detection_failed"
                        else:
                            self._pending_entry_options = options
                            self._pending_entry_data = data_updates
                            self._pending_ev_chargers = detected
                            self._pending_reconfigure = True
                            self._pending_reconfigure_entry = entry
                            return self.async_show_form(
                                step_id="ev_detection",
                                data_schema=vol.Schema({}),
                                description_placeholders=self._ev_detection_placeholders(detected),
                            )
                    else:
                        return self.async_update_reload_and_abort(
                            entry,
                            data_updates=data_updates,
                            options_updates=options,
                        )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=entry.data.get(CONF_HOST, "")): str,
                vol.Required(CONF_PORT, default=entry.data.get(CONF_PORT, DEFAULT_PORT)): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                vol.Required(CONF_UNIT_ID, default=str(entry.data.get(CONF_UNIT_ID, DEFAULT_UNIT_ID))): str,
                vol.Optional(CONF_DEBUG_LOGGING, default=current_options.get(CONF_DEBUG_LOGGING, False)): bool,
                vol.Optional(CONF_SCAN_INTERVAL, default=current_options.get(CONF_SCAN_INTERVAL, 10)): vol.All(vol.Coerce(int), vol.Range(min=2, max=3600)),
                vol.Optional(CONF_ENABLE_GENERATOR, default=current_options.get(CONF_ENABLE_GENERATOR, False)): bool,
                vol.Optional(CONF_ENABLE_EV_CHARGER, default=current_options.get(CONF_ENABLE_EV_CHARGER, False)): bool,
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        return SolarInverterOptionsFlow(config_entry)


class SolarInverterOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def _detect_ev_chargers(self) -> list[int]:
        params = ModbusTcpParams(
            host=self.config_entry.data[CONF_HOST],
            port=self.config_entry.data[CONF_PORT],
        )
        detected: list[int] = []
        async with async_get_temporary_unit(
            self.hass, params, self.config_entry.data[CONF_UNIT_ID]
        ) as unit:
            for charger, base_address in ((1, 3200), (2, 3250)):
                try:
                    status = await unit.read_input_registers(base_address, 1)
                    address = await unit.read_input_registers(base_address + 1, 1)
                    serial = await unit.read_input_registers(base_address + 2, 4)
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug(
                        "EV charger %s is not available at Modbus block %s: %s",
                        charger,
                        base_address,
                        err,
                    )
                    continue

                if (
                    status
                    and int(status[0]) == 1
                    and address
                    and 1 <= int(address[0]) <= 247
                    and serial
                    and any(int(value) != 0 for value in serial)
                ):
                    detected.append(charger)
        return detected

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            if user_input.get(CONF_ENABLE_EV_CHARGER, False):
                try:
                    detected = await self._detect_ev_chargers()
                except Exception as err:  # noqa: BLE001
                    _LOGGER.warning("Unable to detect EV chargers in options flow: %s", err)
                    return self.async_show_form(
                        step_id="init",
                        data_schema=self._schema(),
                        errors={"base": "ev_detection_failed"},
                    )
                user_input[CONF_EV_CHARGERS] = detected
            else:
                user_input[CONF_EV_CHARGERS] = []
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=self._schema())

    def _schema(self):
        return vol.Schema(
            {
                vol.Optional(CONF_DEBUG_LOGGING, default=self.config_entry.options.get(CONF_DEBUG_LOGGING, False)): bool,
                vol.Optional(CONF_SCAN_INTERVAL, default=self.config_entry.options.get(CONF_SCAN_INTERVAL, 10)): vol.All(vol.Coerce(int), vol.Range(min=2, max=3600)),
                vol.Optional(CONF_ENABLE_GENERATOR, default=self.config_entry.options.get(CONF_ENABLE_GENERATOR, False)): bool,
                vol.Optional(CONF_ENABLE_EV_CHARGER, default=self.config_entry.options.get(CONF_ENABLE_EV_CHARGER, False)): bool,
            }
        )
