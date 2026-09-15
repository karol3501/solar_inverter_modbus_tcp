"""Regression tests for Home Assistant device identifiers."""

from types import SimpleNamespace

from custom_components.solar_inverter_modbus_tcp.config_flow import (
    SolarInverterConfigFlow,
)
from custom_components.solar_inverter_modbus_tcp.device import (
    ev_charger_device_info,
    inverter_device_info,
)


def test_inverter_device_is_scoped_to_the_config_entry() -> None:
    coordinator = SimpleNamespace(entry_id="entry-one", data={})

    device = inverter_device_info(coordinator)

    assert device["identifiers"] == {("solar_inverter_modbus_tcp", "solar_inverter_entry-one")}


def test_ev_charger_device_uses_its_serial_number() -> None:
    coordinator = SimpleNamespace(
        entry_id="entry-one",
        data={"r3202": 0, "r3203": 0, "r3204": 0, "r3205": 123456789},
    )

    device = ev_charger_device_info(coordinator, 1)

    assert device["name"] == "EV Charger 123456789"
    assert device["identifiers"] == {
        ("solar_inverter_modbus_tcp", "entry-one_ev_charger_123456789")
    }


def test_config_entry_unique_id_matches_connection_parameters() -> None:
    assert SolarInverterConfigFlow._entry_unique_id("10.20.10.100", 502, 1) == (
        "10.20.10.100:502:1"
    )

