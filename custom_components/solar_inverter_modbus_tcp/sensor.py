from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
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
    modbus_address: int | None = None
    word_count: int = 1


def d(name: str, data_key: str, scale: float = 1.0, unit: str | None = None, device_class: str | None = None, state_class: str | None = None, data_type: str = "uint16", modbus_address: int | None = None, word_count: int = 1) -> SolarSensorDescription:
    if modbus_address is None and data_key.startswith("r"):
        modbus_address = int(data_key[1:])
    return SolarSensorDescription(key=data_key, name=name, data_key=data_key, scale=scale, signed=data_type == "int16", modbus_address=modbus_address, word_count=word_count, native_unit_of_measurement=unit, device_class=_DC.get(device_class) if device_class else None, state_class=_SC.get(state_class) if state_class else None, suggested_display_precision=1 if data_key == "r46" else None)


DESCRIPTION = [
    d("SW Fault", "sw_fault", data_type="uint32", modbus_address=19), d("HW Fault", "r21", data_type="uint32"),
    d("PV1 Voltage", "r27", 0.1, "V", "voltage", "measurement"), d("PV1 Current", "r28", 0.01, "A", "current", "measurement", "int16"), d("PV1 Power", "r29", 1, "W", "power", "measurement"),
    d("PV2 Voltage", "r30", 0.1, "V", "voltage", "measurement"), d("PV2 Current", "r31", 0.01, "A", "current", "measurement", "int16"), d("PV2 Power", "r32", 1, "W", "power", "measurement"),
    d("PV3 Voltage", "r33", 0.1, "V", "voltage", "measurement"), d("PV3 Current", "r34", 0.01, "A", "current", "measurement", "int16"), d("PV3 Power", "r35", 1, "W", "power", "measurement"),
    d("PV4 Voltage", "r36", 0.1, "V", "voltage", "measurement"), d("PV4 Current", "r37", 0.01, "A", "current", "measurement", "int16"), d("PV4 Power", "r38", 1, "W", "power", "measurement"),
    d("GCF Export Soft Limit Ratio", "r259", 0.1, "%", None, "measurement"), d("Battery Voltage", "r46", 0.1, "V", "voltage", "measurement"), d("Battery Current", "r48", 0.01, "A", "current", "measurement", "int32"), d("Battery Power", "r50", 1, "W", "power", "measurement", "int32"),
    d("Grid Voltage L1", "r62", 0.1, "V", "voltage", "measurement"), d("Grid Voltage L2", "r63", 0.1, "V", "voltage", "measurement"), d("Grid Voltage L3", "r64", 0.1, "V", "voltage", "measurement"), d("Grid Frequency", "r66", 0.01, "Hz", None, "measurement"),
    d("Inverter Voltage L1", "r67", 0.1, "V", "voltage", "measurement"), d("Inverter Voltage L2", "r68", 0.1, "V", "voltage", "measurement"), d("Inverter Voltage L3", "r69", 0.1, "V", "voltage", "measurement"), d("Inverter Current L1", "r70", 0.01, "A", "current", "measurement", "int16"), d("Inverter Current L2", "r71", 0.01, "A", "current", "measurement", "int16"), d("Inverter Current L3", "r72", 0.01, "A", "current", "measurement", "int16"),
    d("Inverter Active Power L1", "r74", 1, "W", "power", "measurement", "int16"), d("Inverter Active Power L2", "r75", 1, "W", "power", "measurement", "int16"), d("Inverter Active Power L3", "r76", 1, "W", "power", "measurement", "int16"), d("Backup Voltage A", "r81", 0.1, "V", "voltage", "measurement"), d("Backup Voltage B", "r82", 0.1, "V", "voltage", "measurement"), d("Backup Voltage C", "r83", 0.1, "V", "voltage", "measurement"),
    d("Backup Active Power A", "r92", 1, "W", "power", "measurement", "int16"), d("Backup Active Power B", "r93", 1, "W", "power", "measurement", "int16"), d("Backup Active Power C", "r94", 1, "W", "power", "measurement", "int16"), d("Inverter Temperature", "r113", 1, "°C", "temperature", "measurement", "int16"), d("Battery Temperature", "r114", 1, "°C", "temperature", "measurement", "int16"), d("Ambient Temperature", "r115", 1, "°C", "temperature", "measurement", "int16"),
    d("BMS Link Status", "r1022"), d("BMS Fault Code", "r1023"), d("Battery SOC", "r1025", 1, "%", "battery", "measurement"), d("Grid Meter Link Status", "r1046"), d("Grid Meter Voltage L1", "r1047", 0.1, "V", "voltage", "measurement"), d("Grid Meter Voltage L2", "r1048", 0.1, "V", "voltage", "measurement"), d("Grid Meter Voltage L3", "r1049", 0.1, "V", "voltage", "measurement"), d("DRM Status", "r1060"),
    d("Grid Active Power L1", "r1078", -1, "W", "power", "measurement", "int32"), d("Grid Active Power L2", "r1080", -1, "W", "power", "measurement", "int32"), d("Grid Active Power L3", "r1082", -1, "W", "power", "measurement", "int32"), d("Safety DSP FM Version", "r201"),
    d("PV Total Energy", "r2000", 0.1, "kWh", "energy", "total_increasing", "int32"), d("PV To Battery Energy Total", "r2022", 0.1, "kWh", "energy", "total_increasing", "int32"), d("PV To Load Energy Total", "r2024", 0.1, "kWh", "energy", "total_increasing", "int32"), d("PV To Grid Energy Total", "r2026", 0.1, "kWh", "energy", "total_increasing", "int32"), d("Battery Total Charge Energy", "r2028", 0.1, "kWh", "energy", "total_increasing", "int32"), d("Battery Total Discharge Energy", "r2030", 0.1, "kWh", "energy", "total_increasing", "int32"), d("Grid Energy Import Total", "r2040", 0.1, "kWh", "energy", "total_increasing", "int32"), d("Grid Energy Export Total", "r2048", 0.1, "kWh", "energy", "total_increasing", "int32"), d("Load Energy Use Total", "r2056", 0.1, "kWh", "energy", "total_increasing", "int32"), d("Energy From PV Total", "r2064", 0.1, "kWh", "energy", "total_increasing", "int32"), d("Energy From Battery Total", "r2066", 0.1, "kWh", "energy", "total_increasing", "int32"), d("Energy From Grid Total", "r2068", 0.1, "kWh", "energy", "total_increasing", "int32"),
    d("PV Energy Today", "r2100", 0.1, "kWh", "energy", "total_increasing"), d("PV To Battery Energy Today", "r2111", 0.1, "kWh", "energy", "total_increasing"), d("PV To Load Energy Today", "r2112", 0.1, "kWh", "energy", "total_increasing"), d("PV To Grid Energy Today", "r2113", 0.1, "kWh", "energy", "total_increasing"), d("Battery Charge Energy Today", "r2114", 0.1, "kWh", "energy", "total_increasing"), d("Battery Discharge Energy Today", "r2115", 0.1, "kWh", "energy", "total_increasing"), d("Grid Energy Import Today", "r2120", 0.1, "kWh", "energy", "total_increasing"), d("Grid Energy Export Today", "r2124", 0.1, "kWh", "energy", "total_increasing"), d("Energy From PV Today", "r2132", 0.1, "kWh", "energy", "total_increasing"), d("Energy From Battery Today", "r2133", 0.1, "kWh", "energy", "total_increasing"), d("Energy From Grid Today", "r2134", 0.1, "kWh", "energy", "total_increasing"), d("EMS Mode Raw", "r4300"), d("Peak Meter Power", "r4447", 1, "W", "power", "measurement"), d("Peak Meter SOC Raw", "r4446"),
]

GEN_DESCRIPTION = [d("Generator Voltage L1", "r103", 0.1, "V", "voltage", "measurement"), d("Generator Voltage L2", "r104", 0.1, "V", "voltage", "measurement"), d("Generator Voltage L3", "r105", 0.1, "V", "voltage", "measurement"), d("Generator Current L1", "r106", 0.01, "A", "current", "measurement", "int16"), d("Generator Current L2", "r107", 0.01, "A", "current", "measurement", "int16"), d("Generator Current L3", "r108", 0.01, "A", "current", "measurement", "int16"), d("Generator Active Power L1", "r109", 1, "W", "power", "measurement", "int16"), d("Generator Active Power L2", "r110", 1, "W", "power", "measurement", "int16"), d("Generator Active Power L3", "r111", 1, "W", "power", "measurement", "int16"), d("Generator Energy Today", "r2135", 0.1, "kWh", "energy", "total_increasing")]

EV_CHARGER_1_DESCRIPTION = [d("EV Charger 1 Connection Status", "r3200"), d("EV Charger 1 Communication Address", "r3201"), d("EV Charger 1 Serial Number", "r3202", word_count=4), d("EV Charger 1 Start Mode", "r3206"), d("EV Charger 1 Bill Start Mode", "r3207"), d("EV Charger 1 Bill End Mode", "r3208"), d("EV Charger 1 Software Version", "r3209"), d("EV Charger 1 Type", "r3210"), d("EV Charger 1 Minimum Charge Power", "r3211", 0.1, "kW", "power", "measurement"), d("EV Charger 1 Status", "r3212"), d("EV Charger 1 Error Code", "r3213"), d("EV Charger 1 Rated Power", "r3214"), d("EV Charger 1 Real Output Power", "r3215"), d("EV Charger 1 Output Percentage Set", "r3216"), d("EV Charger 1 Offline Charge Power Limit", "r3217"), d("EV Charger 1 Output Power Set", "r3218"), d("EV Charger 1 Gun Status", "r3219"), d("EV Charger 1 Output Voltage", "r3220", 0.1, "V", "voltage", "measurement"), d("EV Charger 1 Output Current", "r3221", 0.1, "A", "current", "measurement"), d("EV Charger 1 Output Power", "r3222", 0.1, "kW", "power", "measurement"), d("EV Charger 1 Output Time", "r3223", 1, "min", None, "measurement"), d("EV Charger 1 Output Energy", "r3224", 0.1, "kWh", "energy", "measurement")]

EV_CHARGER_2_DESCRIPTION = [d("EV Charger 2 Connection Status", "r3250"), d("EV Charger 2 Communication Address", "r3251"), d("EV Charger 2 Serial Number", "r3252", word_count=4), d("EV Charger 2 Start Mode", "r3256"), d("EV Charger 2 Bill Start Mode", "r3257"), d("EV Charger 2 Bill End Mode", "r3258"), d("EV Charger 2 Software Version", "r3259"), d("EV Charger 2 Type", "r3260"), d("EV Charger 2 Minimum Charge Power", "r3261", 0.1, "kW", "power", "measurement"), d("EV Charger 2 Status", "r3262"), d("EV Charger 2 Error Code", "r3263"), d("EV Charger 2 Rated Power", "r3264"), d("EV Charger 2 Real Output Power", "r3265"), d("EV Charger 2 Output Percentage Set", "r3266"), d("EV Charger 2 Offline Charge Power Limit", "r3267"), d("EV Charger 2 Output Power Set", "r3268"), d("EV Charger 2 Gun Status", "r3269"), d("EV Charger 2 Output Voltage", "r3270", 0.1, "V", "voltage", "measurement"), d("EV Charger 2 Output Current", "r3271", 0.1, "A", "current", "measurement"), d("EV Charger 2 Output Power", "r3272", 0.1, "kW", "power", "measurement"), d("EV Charger 2 Output Time", "r3273", 1, "min", None, "measurement"), d("EV Charger 2 Output Energy", "r3274", 0.1, "kWh", "energy", "measurement")]

DERIVED = [("work_status_text", "Work Status", None, None, None, ()), ("total_pv_power", "Total PV Power", "W", "power", "measurement", ("PV1 Power", "PV2 Power", "PV3 Power", "PV4 Power")), ("total_grid_power", "Total Grid Power", "W", "power", "measurement", ("Grid Active Power L1", "Grid Active Power L2", "Grid Active Power L3")), ("total_inverter_power", "Total Inverter Power", "W", "power", "measurement", ("Inverter Active Power L1", "Inverter Active Power L2", "Inverter Active Power L3")), ("backup_active_power", "Backup Active Power", "W", "power", "measurement", ("Backup Active Power A", "Backup Active Power B", "Backup Active Power C")), ("load_power", "Load Power", "W", "power", "measurement", ("Total Inverter Power", "Total Grid Power"))]


def _device_info(coordinator: SolarInverterCoordinator) -> DeviceInfo:
    return DeviceInfo(identifiers={(DOMAIN, "solar_inverter")}, name="Solar Inverter", manufacturer="Generic", model="Modbus TCP")


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SolarInverterCoordinator = entry.runtime_data
    descriptions = list(DESCRIPTION)
    if coordinator.enable_generator:
        descriptions.extend(GEN_DESCRIPTION)
    if coordinator.enable_ev_charger:
        if 1 in coordinator.ev_chargers:
            descriptions.extend(EV_CHARGER_1_DESCRIPTION)
        if 2 in coordinator.ev_chargers:
            descriptions.extend(EV_CHARGER_2_DESCRIPTION)
    entities: list[SensorEntity] = [SolarInverterSensor(coordinator, description) for description in descriptions]
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
        if self.entity_description.data_key == "r1023":
            return "No Fault" if int(value) == 0 else "Fault"
        if self.entity_description.word_count == 4:
            values = [self.coordinator.data.get(f"r{int(self.entity_description.data_key[1:]) + offset}") for offset in range(4)]
            if any(item is None for item in values):
                return None
            return (int(values[0]) << 48) | (int(values[1]) << 32) | (int(values[2]) << 16) | int(values[3])
        value = int(value)
        if self.entity_description.signed and value & 0x8000:
            value -= 0x10000
        return value * self.entity_description.scale

    @property
    def extra_state_attributes(self):
        if self.entity_description.modbus_address is None:
            return None
        return {"modbus_address": self.entity_description.modbus_address}


class SolarDerivedSensor(CoordinatorEntity[SolarInverterCoordinator], SensorEntity):
    def __init__(self, coordinator: SolarInverterCoordinator, data_key: str, name: str, unit: str | None, device_class: str | None, state_class: str | None, source_sensors: tuple[str, ...]) -> None:
        super().__init__(coordinator)
        self._data_key = data_key
        self._source_sensors = source_sensors
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

    @property
    def extra_state_attributes(self):
        return {"calculated": True, "source_sensors": list(self._source_sensors)}


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
    def native_value(self) -> StateType:
        total = self.coordinator.data.get("r2056")
        if total is None:
            return None
        total = int(total) * 0.1
        today = dt_util.now().date().isoformat()
        if self._reset_date != today:
            self._baseline = total
            self._reset_date = today
        if self._baseline is None:
            self._baseline = total
        return max(0.0, total - self._baseline)

    @property
    def extra_state_attributes(self):
        return {"calculated": True, "source_sensors": ["Load Energy Use Total"]}


class SolarInverterEmsModeSensor(CoordinatorEntity[SolarInverterCoordinator], SensorEntity):
    _attr_name = "EMS Mode"
    _attr_has_entity_name = True

    def __init__(self, coordinator: SolarInverterCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_ems_mode"
        self._attr_device_info = _device_info(coordinator)

    @property
    def native_value(self) -> StateType:
        value = self.coordinator.data.get("ems_mode")
        return EMS_MODES.get(int(value)) if value is not None else None

    @property
    def extra_state_attributes(self):
        return {"modbus_address": 4300}
