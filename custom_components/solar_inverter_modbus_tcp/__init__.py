from __future__ import annotations

import logging

from homeassistant.components.modbus import async_get_unit
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify
from modbus_connection import ModbusTcpParams

from .const import (
    CONF_DEBUG_LOGGING,
    CONF_ENABLE_EV_CHARGER,
    CONF_ENABLE_GENERATOR,
    CONF_EV_CHARGERS,
    CONF_EV_CHARGER_1_RATED_POWER_KW,
    CONF_EV_CHARGER_2_RATED_POWER_KW,
    CONF_EXPORT_LIMIT_WATTS,
    CONF_INVERTER_RATED_POWER_WATTS,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_EXPORT_LIMIT_WATTS,
    DEFAULT_INVERTER_RATED_POWER_WATTS,
    DOMAIN,
)
from .coordinator import SolarInverterCoordinator
from .sensor import (
    EV_CHARGER_1_DESCRIPTION,
    EV_CHARGER_2_DESCRIPTION,
    GEN_DESCRIPTION,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "select", "number", "time"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    params = ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT])
    unit = async_get_unit(hass, entry, params, entry.data[CONF_UNIT_ID])
    detected_ev_chargers = entry.options.get(CONF_EV_CHARGERS)
    coordinator = SolarInverterCoordinator(
        hass,
        unit,
        entry.entry_id,
        update_interval=entry.options.get(CONF_SCAN_INTERVAL, 10),
        debug_logging=entry.options.get(CONF_DEBUG_LOGGING, False),
        enable_generator=entry.options.get(CONF_ENABLE_GENERATOR, False),
        enable_ev_charger=entry.options.get(CONF_ENABLE_EV_CHARGER, False),
        ev_chargers=detected_ev_chargers,
        export_limit_watts=entry.options.get(
            CONF_EXPORT_LIMIT_WATTS, DEFAULT_EXPORT_LIMIT_WATTS
        ),
        inverter_rated_power_watts=entry.options.get(
            CONF_INVERTER_RATED_POWER_WATTS,
            DEFAULT_INVERTER_RATED_POWER_WATTS,
        ),
        ev_charger_1_rated_power_kw=entry.options.get(CONF_EV_CHARGER_1_RATED_POWER_KW, 11.0),
        ev_charger_2_rated_power_kw=entry.options.get(CONF_EV_CHARGER_2_RATED_POWER_KW, 11.0),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    _async_migrate_sensor_entity_ids(hass, coordinator)
    _async_sync_optional_sensor_entities(hass, coordinator)
    _async_disable_deprecated_tou_number_entities(hass, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _async_migrate_sensor_entity_ids(
    hass: HomeAssistant, coordinator: SolarInverterCoordinator
) -> None:
    """Move selected default sensor entity IDs without changing unique IDs."""
    registry = er.async_get(hass)
    migrations = [
        (
            f"{DOMAIN}_{coordinator.entry_id}_total_grid_power",
            "sensor.solar_inverter_grid_active_power",
        )
    ]
    for charger, descriptions in (
        (1, EV_CHARGER_1_DESCRIPTION),
        (2, EV_CHARGER_2_DESCRIPTION),
    ):
        for description in descriptions:
            suffix = slugify(
                description.name.removeprefix(f"EV Charger {charger} ")
            )
            migrations.append(
                (
                    f"{DOMAIN}_{coordinator.entry_id}_{description.key}",
                    f"sensor.ev_charger{charger}_{suffix}",
                )
            )

    for unique_id, new_entity_id in migrations:
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        if entity_id is None or entity_id == new_entity_id:
            continue
        if registry.async_get(new_entity_id) is not None:
            _LOGGER.warning(
                "ENTITY ID MIGRATION SKIPPED | source=%s | target=%s already exists",
                entity_id,
                new_entity_id,
            )
            continue
        registry.async_update_entity(entity_id, new_entity_id=new_entity_id)


def _async_disable_deprecated_tou_number_entities(
    hass: HomeAssistant, coordinator: SolarInverterCoordinator
) -> None:
    """Hide superseded TOU hour/minute number entities."""
    registry = er.async_get(hass)
    data_keys = (
        "tou_period_1_charge_start_hour",
        "tou_period_1_charge_start_minute",
        "tou_period_1_charge_end_hour",
        "tou_period_1_charge_end_minute",
        "tou_period_1_discharge_start_hour",
        "tou_period_1_discharge_start_minute",
        "tou_period_1_discharge_end_hour",
        "tou_period_1_discharge_end_minute",
    )
    for data_key in data_keys:
        unique_id = f"{DOMAIN}_{coordinator.entry_id}_{data_key}"
        entity_id = registry.async_get_entity_id("number", DOMAIN, unique_id)
        if entity_id is None:
            continue
        registry_entry = registry.async_get(entity_id)
        if registry_entry and registry_entry.disabled_by is None:
            registry.async_update_entity(
                entity_id,
                disabled_by=er.RegistryEntryDisabler.INTEGRATION,
            )


def _async_sync_optional_sensor_entities(
    hass: HomeAssistant, coordinator: SolarInverterCoordinator
) -> None:
    """Hide disabled optional sensors without losing their registry entries."""
    registry = er.async_get(hass)
    ev_chargers = set(coordinator.ev_chargers or [])
    optional_groups = (
        (coordinator.enable_generator, GEN_DESCRIPTION),
        (
            coordinator.enable_ev_charger and 1 in ev_chargers,
            EV_CHARGER_1_DESCRIPTION,
        ),
        (
            coordinator.enable_ev_charger and 2 in ev_chargers,
            EV_CHARGER_2_DESCRIPTION,
        ),
    )

    for enabled, descriptions in optional_groups:
        for description in descriptions:
            unique_id = f"{DOMAIN}_{coordinator.entry_id}_{description.key}"
            entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
            if entity_id is None:
                continue

            registry_entry = registry.async_get(entity_id)
            if registry_entry is None:
                continue

            if enabled and registry_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
                registry.async_update_entity(entity_id, disabled_by=None)
            elif not enabled and registry_entry.disabled_by is None:
                registry.async_update_entity(
                    entity_id,
                    disabled_by=er.RegistryEntryDisabler.INTEGRATION,
                )


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

