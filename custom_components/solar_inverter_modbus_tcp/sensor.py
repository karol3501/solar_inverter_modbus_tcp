from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, EMS_MODES
from .coordinator import SolarInverterCoordinator


@dataclass(frozen=True, kw_only=True)
class SolarSensorDescription(SensorEntityDescription):
    data_key: str


DESCRIPTION = [
    SolarSensorDescription(
        key="pv_total_power", data_key="r26", name="PV Total Power",
        device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W",
        state_class="measurement",
    ),
    SolarSensorDescription(key="pv1_voltage", data_key="r27", name="PV1 Voltage", device_class=SensorDeviceClass.VOLTAGE, native_unit_of_measurement="V", state_class="measurement"),
    SolarSensorDescription(key="pv1_current", data_key="r28", name="PV1 Current", device_class=SensorDeviceClass.CURRENT, native_unit_of_measurement="A", state_class="measurement"),
    SolarSensorDescription(key="pv1_power", data_key="r29", name="PV1 Power", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="pv2_voltage", data_key="r30", name="PV2 Voltage", device_class=SensorDeviceClass.VOLTAGE, native_unit_of_measurement="V", state_class="measurement"),
    SolarSensorDescription(key="pv2_current", data_key="r31", name="PV2 Current", device_class=SensorDeviceClass.CURRENT, native_unit_of_measurement="A", state_class="measurement"),
    SolarSensorDescription(key="pv2_power", data_key="r32", name="PV2 Power", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="pv3_voltage", data_key="r33", name="PV3 Voltage", device_class=SensorDeviceClass.VOLTAGE, native_unit_of_measurement="V", state_class="measurement"),
    SolarSensorDescription(key="pv3_current", data_key="r34", name="PV3 Current", device_class=SensorDeviceClass.CURRENT, native_unit_of_measurement="A", state_class="measurement"),
    SolarSensorDescription(key="pv3_power", data_key="r35", name="PV3 Power", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="pv4_voltage", data_key="r36", name="PV4 Voltage", device_class=SensorDeviceClass.VOLTAGE, native_unit_of_measurement="V", state_class="measurement"),
    SolarSensorDescription(key="pv4_current", data_key="r37", name="PV4 Current", device_class=SensorDeviceClass.CURRENT, native_unit_of_measurement="A", state_class="measurement"),
    SolarSensorDescription(key="pv4_power", data_key="r38", name="PV4 Power", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="battery_power", data_key="battery_power", name="Battery Power", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="battery_voltage", data_key="r46", name="Battery Voltage", device_class=SensorDeviceClass.VOLTAGE, native_unit_of_measurement="V", state_class="measurement"),
    SolarSensorDescription(key="battery_current", data_key="battery_current", name="Battery Current", device_class=SensorDeviceClass.CURRENT, native_unit_of_measurement="A", state_class="measurement"),
    SolarSensorDescription(key="grid_voltage_a", data_key="r62", name="Grid Voltage A", device_class=SensorDeviceClass.VOLTAGE, native_unit_of_measurement="V", state_class="measurement"),
    SolarSensorDescription(key="grid_voltage_b", data_key="r63", name="Grid Voltage B", device_class=SensorDeviceClass.VOLTAGE, native_unit_of_measurement="V", state_class="measurement"),
    SolarSensorDescription(key="grid_voltage_c", data_key="r64", name="Grid Voltage C", device_class=SensorDeviceClass.VOLTAGE, native_unit_of_measurement="V", state_class="measurement"),
    SolarSensorDescription(key="grid_frequency", data_key="r66", name="Grid Frequency", device_class=SensorDeviceClass.FREQUENCY, native_unit_of_measurement="Hz", state_class="measurement"),
    SolarSensorDescription(key="grid_active_power_a", data_key="r1078", name="Grid Active Power A", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="grid_active_power_b", data_key="r1080", name="Grid Active Power B", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="grid_active_power_c", data_key="r1082", name="Grid Active Power C", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="grid_reactive_power_a", data_key="r1084", name="Grid Reactive Power A", native_unit_of_measurement="var", state_class="measurement"),
    SolarSensorDescription(key="grid_reactive_power_b", data_key="r1086", name="Grid Reactive Power B", native_unit_of_measurement="var", state_class="measurement"),
    SolarSensorDescription(key="grid_reactive_power_c", data_key="r1088", name="Grid Reactive Power C", native_unit_of_measurement="var", state_class="measurement"),
    SolarSensorDescription(key="inverter_voltage_a", data_key="r67", name="Inverter Voltage A", device_class=SensorDeviceClass.VOLTAGE, native_unit_of_measurement="V", state_class="measurement"),
    SolarSensorDescription(key="inverter_voltage_b", data_key="r68", name="Inverter Voltage B", device_class=SensorDeviceClass.VOLTAGE, native_unit_of_measurement="V", state_class="measurement"),
    SolarSensorDescription(key="inverter_voltage_c", data_key="r69", name="Inverter Voltage C", device_class=SensorDeviceClass.VOLTAGE, native_unit_of_measurement="V", state_class="measurement"),
    SolarSensorDescription(key="inverter_current_a", data_key="r70", name="Inverter Current A", device_class=SensorDeviceClass.CURRENT, native_unit_of_measurement="A", state_class="measurement"),
    SolarSensorDescription(key="inverter_current_b", data_key="r71", name="Inverter Current B", device_class=SensorDeviceClass.CURRENT, native_unit_of_measurement="A", state_class="measurement"),
    SolarSensorDescription(key="inverter_current_c", data_key="r72", name="Inverter Current C", device_class=SensorDeviceClass.CURRENT, native_unit_of_measurement="A", state_class="measurement"),
    SolarSensorDescription(key="inverter_active_power", data_key="r73", name="Inverter Active Power", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="inverter_active_power_a", data_key="r74", name="Inverter Active Power A", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="inverter_active_power_b", data_key="r75", name="Inverter Active Power B", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="inverter_active_power_c", data_key="r76", name="Inverter Active Power C", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="inverter_reactive_power", data_key="r77", name="Inverter Reactive Power", native_unit_of_measurement="var", state_class="measurement"),
    SolarSensorDescription(key="inverter_reactive_power_a", data_key="r78", name="Inverter Reactive Power A", native_unit_of_measurement="var", state_class="measurement"),
    SolarSensorDescription(key="inverter_reactive_power_b", data_key="r79", name="Inverter Reactive Power B", native_unit_of_measurement="var", state_class="measurement"),
    SolarSensorDescription(key="inverter_reactive_power_c", data_key="r80", name="Inverter Reactive Power C", native_unit_of_measurement="var", state_class="measurement"),
    SolarSensorDescription(key="backup_voltage_a", data_key="r81", name="Backup Voltage A", device_class=SensorDeviceClass.VOLTAGE, native_unit_of_measurement="V", state_class="measurement"),
    SolarSensorDescription(key="backup_voltage_b", data_key="r82", name="Backup Voltage B", device_class=SensorDeviceClass.VOLTAGE, native_unit_of_measurement="V", state_class="measurement"),
    SolarSensorDescription(key="backup_voltage_c", data_key="r83", name="Backup Voltage C", device_class=SensorDeviceClass.VOLTAGE, native_unit_of_measurement="V", state_class="measurement"),
    SolarSensorDescription(key="backup_current_a", data_key="r84", name="Backup Current A", device_class=SensorDeviceClass.CURRENT, native_unit_of_measurement="A", state_class="measurement"),
    SolarSensorDescription(key="backup_current_b", data_key="r85", name="Backup Current B", device_class=SensorDeviceClass.CURRENT, native_unit_of_measurement="A", state_class="measurement"),
    SolarSensorDescription(key="backup_current_c", data_key="r86", name="Backup Current C", device_class=SensorDeviceClass.CURRENT, native_unit_of_measurement="A", state_class="measurement"),
    SolarSensorDescription(key="backup_apparent_power", data_key="r87", name="Backup Apparent Power", native_unit_of_measurement="VA", state_class="measurement"),
    SolarSensorDescription(key="backup_apparent_power_a", data_key="r88", name="Backup Apparent Power A", native_unit_of_measurement="VA", state_class="measurement"),
    SolarSensorDescription(key="backup_apparent_power_b", data_key="r89", name="Backup Apparent Power B", native_unit_of_measurement="VA", state_class="measurement"),
    SolarSensorDescription(key="backup_apparent_power_c", data_key="r90", name="Backup Apparent Power C", native_unit_of_measurement="VA", state_class="measurement"),
    SolarSensorDescription(key="backup_active_power", data_key="r91", name="Backup Active Power", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="backup_active_power_a", data_key="r92", name="Backup Active Power A", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="backup_active_power_b", data_key="r93", name="Backup Active Power B", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="backup_active_power_c", data_key="r94", name="Backup Active Power C", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="pv_inverter_power_a", data_key="r1090", name="PV Inverter Active Power A", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="pv_inverter_power_b", data_key="r1092", name="PV Inverter Active Power B", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
    SolarSensorDescription(key="pv_inverter_power_c", data_key="r1094", name="PV Inverter Active Power C", device_class=SensorDeviceClass.POWER, native_unit_of_measurement="W", state_class="measurement"),
]


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SolarInverterCoordinator = entry.runtime_data
    entities = [SolarInverterSensor(coordinator, description) for description in DESCRIPTION]
    entities.append(SolarInverterEmsModeSensor(coordinator))
    async_add_entities(entities)


class SolarInverterSensor(CoordinatorEntity[SolarInverterCoordinator], SensorEntity):
    def __init__(self, coordinator: SolarInverterCoordinator, description: SolarSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "solar_inverter")},
            "name": "Solar Inverter",
            "manufacturer": "Generic",
            "model": "Modbus TCP",
        }

    @property
    def native_value(self) -> StateType:
        return self.coordinator.data.get(self.entity_description.data_key)


class SolarInverterEmsModeSensor(CoordinatorEntity[SolarInverterCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "EMS Mode (4300)"

    def __init__(self, coordinator: SolarInverterCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_ems_mode"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "solar_inverter")},
            "name": "Solar Inverter",
            "manufacturer": "Generic",
            "model": "Modbus TCP",
        }

    @property
    def native_value(self) -> str | None:
        value = self.coordinator.data.get("ems_mode")
        if value is None:
            return None
        return EMS_MODES.get(int(value), f"Unknown ({value})")
