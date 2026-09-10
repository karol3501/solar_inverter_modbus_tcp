from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

from .const import DOMAIN, EMS_MODES
from .coordinator import SolarInverterCoordinator

_DC = {"voltage": SensorDeviceClass.VOLTAGE, "current": SensorDeviceClass.CURRENT, "power": SensorDeviceClass.POWER, "temperature": SensorDeviceClass.TEMPERATURE, "battery": SensorDeviceClass.BATTERY, "energy": SensorDeviceClass.ENERGY}
_SC = {"measurement": SensorStateClass.MEASUREMENT, "total_increasing": SensorStateClass.TOTAL_INCREASING}

@dataclass(frozen=True, kw_only=True)
class SolarSensorDescription(SensorEntityDescription):
    data_key: str
    scale: float = 1.0
    signed: bool = False


def d(name: str, data_key: str, scale: float = 1.0, unit: str | None = None, device_class: str | None = None, state_class: str | None = None, data_type: str = "uint16") -> SolarSensorDescription:
    return SolarSensorDescription(key=data_key, name=name, data_key=data_key, scale=scale, signed=data_type == "int16", native_unit_of_measurement=unit, device_class=_DC.get(device_class) if device_class else None, state_class=_SC.get(state_class) if state_class else None)

DESCRIPTION = [
    d("Work Status", "r0"), d("SW Fault", "sw_fault", data_type="uint32"),
    d("PV1 Voltage", "r27", 0.1, "V", "voltage", "measurement"), d("PV1 Current", "r28", 0.01, "A", "current", "measurement", "int16"), d("PV1 Power", "r29", 1, "W", "power", "measurement"),
    d("PV2 Voltage", "r30", 0.1, "V", "voltage", "measurement"), d("PV2 Current", "r31", 0.01, "A", "current", "measurement", "int16"), d("PV2 Power", "r32", 1, "W", "power", "measurement"),
    d("PV3 Voltage", "r33", 0.1, "V", "voltage", "measurement"), d("PV3 Current", "r34", 0.01, "A", "current", "measurement", "int16"), d("PV3 Power", "r35", 1, "W", "power", "measurement"),
    d("PV4 Voltage", "r36", 0.1, "V", "voltage", "measurement"), d("PV4 Current", "r37", 0.01, "A", "current", "measurement", "int16"), d("PV4 Power", "r38", 1, "W", "power", "measurement"),
    d("GCF Export Soft Limit Ratio", "r259", 0.1, "%", None, "measurement"),
    d("Battery Voltage", "r46", 0.1, "V", "voltage", "measurement"), d("Battery Current", "r48", 0.01, "A", "current", "measurement", "int32"), d("Battery Power", "r50", 1, "W", "power", "measurement", "int32"),
    d("Grid Voltage L1", "r62", 0.1, "V", "voltage", "measurement"), d("Grid Voltage L2", "r63", 0.1, "V", "voltage", "measurement"), d("Grid Voltage L3", "r64", 0.1, "V", "voltage", "measurement"), d("Grid Frequency", "r66", 0.01, "Hz", None, "measurement"),
    d("Inverter Voltage L1", "r67", 0.1, "V", "voltage", "measurement"), d("Inverter Voltage L2", "r68", 0.1, "V", "voltage", "measurement"), d("Inverter Voltage L3", "r69", 0.1, "V", "voltage", "measurement"),
    d("Inverter Current L1", "r70", 0.01, "A", "current", "measurement", "int16"), d("Inverter Current L2", "r71", 0.01, "A", "current", "measurement", "int16"), d("Inverter Current L3", "r72", 0.01, "A", "current", "measurement", "int16"),
    d("Inverter Active Power", "r73", 1, "W", "power", "measurement", "int16"), d("Inverter Active Power L1", "r74", 1, "W", "power", "measurement", "int16"), d("Inverter Active Power L2", "r75", 1, "W", "power", "measurement", "int16"), d("Inverter Active Power L3", "r76", 1, "W", "power", "measurement", "int16"),
    d("Inverter Reactive Power", "r77", 1, "var", None, "measurement", "int16"), d("Inverter Reactive Power L1", "r78", 1, "var", None, "measurement", "int16"), d("Inverter Reactive Power L2", "r79", 1, "var", None, "measurement", "int16"), d("Inverter Reactive Power L3", "r80", 1, "var", None, "measurement", "int16"),
    d("Backup Voltage A", "r81", 0.1, "V", "voltage", "measurement"), d("Backup Voltage B", "r82", 0.1, "V", "voltage", "measurement"), d("Backup Voltage C", "r83", 0.1, "V", "voltage", "measurement"),
    d("Backup Current A", "r84", 0.01, "A", "current", "measurement", "int16"), d("Backup Current B", "r85", 0.01, "A", "current", "measurement", "int16"), d("Backup Current C", "r86", 0.01, "A", "current", "measurement", "int16"),
    d("Backup Apparent Power", "r87", 1, "VA", None, "measurement", "int16"), d("Backup Apparent Power A", "r88", 1, "VA", None, "measurement", "int16"), d("Backup Apparent Power B", "r89", 1, "VA", None, "measurement", "int16"), d("Backup Apparent Power C", "r90", 1, "VA", None, "measurement", "int16"),
    d("Backup Active Power", "r91", 1, "W", "power", "measurement", "int16"), d("Backup Active Power A", "r92", 1, "W", "power", "measurement", "int16"), d("Backup Active Power B", "r93", 1, "W", "power", "measurement", "int16"), d("Backup Active Power C", "r94", 1, "W", "power", "measurement", "int16"),
    d("Inverter Temperature", "r113", 1, "°C", "temperature", "measurement", "int16"), d("Battery Temperature", "r114", 1, "°C", "temperature", "measurement", "int16"), d("Ambient Temperature", "r115", 1, "°C", "temperature", "measurement", "int16"),
    d("BMS Link Status", "r1022"), d("BMS Fault Code", "r1023"), d("Battery SOC", "r1025", 1, "%", "battery", "measurement"), d("Grid Side Meter Link Status", "r1046"), d("DRM Status", "r1060"),
    d("Grid Active Power L1", "r1078", -1, "W", "power", "measurement", "int32"), d("Grid Active Power L2", "r1080", -1, "W", "power", "measurement", "int32"), d("Grid Active Power L3", "r1082", -1, "W", "power", "measurement", "int32"),
    d("Grid Reactive Power L1", "r1084", 1, "var", None, "measurement", "int32"), d("Grid Reactive Power L2", "r1086", 1, "var", None, "measurement", "int32"), d("Grid Reactive Power L3", "r1088", 1, "var", None, "measurement", "int32"), d("PV Inverter Active Power A", "r1090", 1, "W", "power", "measurement", "int32"), d("PV Inverter Active Power B", "r1092", 1, "W", "power", "measurement", "int32"), d("PV Inverter Active Power C", "r1094", 1, "W", "power", "measurement", "int32"),
    d("Safety DSP FM Version", "r201"), d("ReConnect Counter", "r210", 1, "s", None, "measurement"), d("PF Voltage", "r241", 0.1, "V", "voltage", "measurement", "int16"), d("Iso Resistor", "r242", 1, "kΩ", None, "measurement"), d("Residual Current", "r243", 1, "mA", None, "measurement", "int16"),
    d("PV Total Energy", "r2000", 0.1, "kWh", "energy", "total_increasing", "int32"), d("PV To Battery Energy Total", "r2022", 0.1, "kWh", "energy", "total_increasing", "int32"), d("PV To Load Energy Total", "r2024", 0.1, "kWh", "energy", "total_increasing", "int32"), d("PV To Grid Energy Total", "r2026", 0.1, "kWh", "energy", "total_increasing", "int32"), d("Battery Total Charge Energy", "r2028", 0.1, "kWh", "energy", "total_increasing", "int32"), d("Battery Total Discharge Energy", "r2030", 0.1, "kWh", "energy", "total_increasing", "int32"), d("Grid Energy Import Total", "r2040", 0.1, "kWh", "energy", "total_increasing", "int32"), d("Grid Energy Export Total", "r2048", 0.1, "kWh", "energy", "total_increasing", "int32"), d("Load Energy Use Total", "r2056", 0.1, "kWh", "energy", "total_increasing", "int32"), d("Energy From PV Total", "r2064", 0.1, "kWh", "energy", "total_increasing", "int32"), d("Energy From Battery Total", "r2066", 0.1, "kWh", "energy", "total_increasing", "int32"), d("Energy From Grid Total", "r2068", 0.1, "kWh", "energy", "total_increasing", "int32"),
    d("PV Energy Today", "r2100", 0.1, "kWh", "energy", "total_increasing"), d("PV To Battery Energy Today", "r2111", 0.1, "kWh", "energy", "total_increasing"), d("PV To Load Energy Today", "r2112", 0.1, "kWh", "energy", "total_increasing"), d("PV To Grid Energy Today", "r2113", 0.1, "kWh", "energy", "total_increasing"), d("Battery Charge Energy Today", "r2114", 0.1, "kWh", "energy", "total_increasing"), d("Battery Discharge Energy Today", "r2115", 0.1, "kWh", "energy", "total_increasing"), d("Grid Energy Import Today", "r2120", 0.1, "kWh", "energy", "total_increasing"), d("Grid Energy Export Today", "r2124", 0.1, "kWh", "energy", "total_increasing"), d("Energy From Battery Today", "r2133", 0.1, "kWh", "energy", "total_increasing"), d("Energy From Grid Today", "r2134", 0.1, "kWh", "energy", "total_increasing"), d("Gen Energy Total Today", "r2135", 0.1, "kWh", "energy", "total_increasing"),
    d("EMS Mode Raw", "r4300"), d("Peak Meter Power", "r4447", 1, "W", "power", "measurement"), d("Peak Meter SOC Raw", "r4446"),
]

DERIVED = [("work_status_text", "Work Status Text", None, None, None), ("total_pv_power", "Total PV Power", "W", "power", "measurement"), ("total_grid_power", "Total Grid Power", "W", "power", "measurement"), ("total_inverter_power", "Total Inverter Power", "W", "power", "measurement"), ("load_power", "Load Power", "W", "power", "measurement")]


def _device_info(coordinator: SolarInverterCoordinator) -> DeviceInfo:
    return DeviceInfo(identifiers={(DOMAIN, "solar_inverter")}, name="Solar Inverter", manufacturer="Generic", model="Modbus TCP")


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SolarInverterCoordinator = entry.runtime_data
    entities: list[SensorEntity] = [SolarInverterSensor(coordinator, description) for description in DESCRIPTION]
    entities.extend(SolarDerivedSensor(coordinator, *item) for item in DERIVED)
    entities.append(SolarLoadEnergyTodaySensor(coordinator))
    entities.append(SolarInverterEmsModeSensor(coordinator))
    async_add_entities(entities)


class SolarInverterSensor(CoordinatorEntity[SolarInverterCoordinator], SensorEntity):
    def __init__(self, coordinator: SolarInverterCoordinator, description: SolarSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_device_info = _device_info(coordinator)

    @property
    def native_value(self) -> StateType:
        value = self.coordinator.data.get(self.entity_description.data_key)
        if value is None:
            return None
        value = int(value)
        if self.entity_description.signed and value & 0x8000:
            value -= 0x10000
        return value * self.entity_description.scale


class SolarDerivedSensor(CoordinatorEntity[SolarInverterCoordinator], SensorEntity):
    def __init__(self, coordinator: SolarInverterCoordinator, data_key: str, name: str, unit: str | None, device_class: str | None, state_class: str | None) -> None:
        super().__init__(coordinator)
        self._data_key = data_key
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_{data_key}"
        self._attr_has_entity_name = True
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = _DC.get(device_class) if device_class else None
        self._attr_state_class = _SC.get(state_class) if state_class else None
        self._attr_device_info = _device_info(coordinator)

    @property
    def native_value(self) -> StateType:
        return self.coordinator.data.get(self._data_key)


class SolarLoadEnergyTodaySensor(CoordinatorEntity[SolarInverterCoordinator], SensorEntity, RestoreEntity):
    _attr_name = "Load Energy Today"
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: SolarInverterCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_load_energy_today"
        self._attr_device_info = _device_info(coordinator)
        self._baseline: float | None = None
        self._reset_date: str | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state:
            self._baseline = state.attributes.get("baseline_total")
            self._reset_date = state.attributes.get("reset_date")

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {"baseline_total": self._baseline, "reset_date": self._reset_date}

    @property
    def native_value(self) -> float | None:
        total_raw = self.coordinator.data.get("r2056")
        if total_raw is None:
            return None
        total = int(total_raw) * 0.1
        today = dt_util.now().date().isoformat()
        if self._baseline is None or self._reset_date != today:
            self._baseline = total
            self._reset_date = today
        if total < self._baseline:
            self._baseline = total
        return round(max(0.0, total - self._baseline), 3)


class SolarInverterEmsModeSensor(CoordinatorEntity[SolarInverterCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "EMS Mode (4300)"

    def __init__(self, coordinator: SolarInverterCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_ems_mode"
        self._attr_device_info = _device_info(coordinator)

    @property
    def native_value(self) -> str | None:
        value = self.coordinator.data.get("ems_mode")
        if value is None:
            return None
        return EMS_MODES.get(int(value), f"Unknown ({value})")
