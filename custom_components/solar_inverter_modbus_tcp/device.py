"""Home Assistant device definitions for the integration."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import SolarInverterCoordinator


def inverter_device_info(coordinator: SolarInverterCoordinator) -> DeviceInfo:
    """Return the device shared by entities from one config entry."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"solar_inverter_{coordinator.entry_id}")},
        name="Solar Inverter",
        manufacturer="Generic",
        model="Modbus TCP",
    )


def ev_charger_device_info(
    coordinator: SolarInverterCoordinator, charger: int
) -> DeviceInfo:
    """Return the device for a detected EV charger."""
    serial_address = 3202 if charger == 1 else 3252
    serial_words = [
        coordinator.data.get(f"r{serial_address + offset}") for offset in range(4)
    ]
    if any(word is None for word in serial_words):
        raise ValueError(f"EV charger {charger} does not have a serial number")

    serial_number = str(
        (int(serial_words[0]) << 48)
        | (int(serial_words[1]) << 32)
        | (int(serial_words[2]) << 16)
        | int(serial_words[3])
    )
    return DeviceInfo(
        identifiers={(DOMAIN, f"{coordinator.entry_id}_ev_charger_{serial_number}")},
        name=f"EV Charger {serial_number}",
        manufacturer="Hoymiles",
        model="EV Charger",
    )

