"""Regression tests for optional entity registry handling."""

from types import SimpleNamespace

from homeassistant.helpers import entity_registry as er

from custom_components.solar_inverter_modbus_tcp import (
    _async_sync_optional_sensor_entities,
)
from custom_components.solar_inverter_modbus_tcp.const import DOMAIN


class FakeEntityRegistry:
    """Minimal entity registry used to verify optional-entity transitions."""

    def __init__(self) -> None:
        self.entries = {}

    def async_get_entity_id(self, domain: str, platform: str, unique_id: str):
        entity_id = f"{domain}.{unique_id}"
        return entity_id if entity_id in self.entries else None

    def async_get(self, entity_id: str):
        return self.entries.get(entity_id)

    def async_update_entity(self, entity_id: str, *, disabled_by):
        self.entries[entity_id].disabled_by = disabled_by


def test_optional_entities_are_disabled_and_reenabled(monkeypatch) -> None:
    registry = FakeEntityRegistry()
    generator_id = f"sensor.{DOMAIN}_entry-one_r103"
    ev_id = f"sensor.{DOMAIN}_entry-one_r3200"
    registry.entries = {
        generator_id: SimpleNamespace(disabled_by=None),
        ev_id: SimpleNamespace(disabled_by=None),
    }
    monkeypatch.setattr(er, "async_get", lambda hass: registry)
    coordinator = SimpleNamespace(
        entry_id="entry-one",
        enable_generator=False,
        enable_ev_charger=False,
        ev_chargers=[],
    )

    _async_sync_optional_sensor_entities(None, coordinator)

    assert registry.entries[generator_id].disabled_by == er.RegistryEntryDisabler.INTEGRATION
    assert registry.entries[ev_id].disabled_by == er.RegistryEntryDisabler.INTEGRATION

    coordinator.enable_generator = True
    coordinator.enable_ev_charger = True
    coordinator.ev_chargers = [1]
    _async_sync_optional_sensor_entities(None, coordinator)

    assert registry.entries[generator_id].disabled_by is None
    assert registry.entries[ev_id].disabled_by is None
