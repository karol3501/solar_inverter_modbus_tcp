from __future__ import annotations


def _raw_register_info(data_key: str) -> tuple[str, int, str] | None:
    if not data_key.startswith("r") or not data_key[1:].isdigit():
        return None
    address = int(data_key[1:])
    i32_starts = {
        19, 48, 50, 1078, 1080, 1082, 1084, 1086, 1088, 1090, 1092, 1094,
        2000, 2022, 2024, 2026, 2028, 2030, 2040, 2048, 2056, 2064, 2066, 2068,
    }
    function = "FC03" if address in {259, 4300, 4446, 4447} else "FC04"
    count = 2 if address in i32_starts else 1
    return function, address, f"{address}-{address + count - 1}"


def _attrs(function: str, address: int, registers: str, source: str | None = None) -> dict[str, str]:
    result = {
        "modbus_function": function,
        "modbus_address": str(address),
        "modbus_registers": registers,
    }
    if source:
        result["modbus_source"] = source
    return result


STATUS_ENTITIES = {
    "r1022": ("BMS Link Status", {0: "Disconnected", 1: "Connected"}),
    "r1023": ("BMS Fault Status", {0: "No Fault"}),
    "r1046": ("Grid Meter Link Status", {0: "Disconnected", 1: "Connected"}),
    "r1060": ("DRM Status", {0: "Inactive", 1: "Active"}),
}


def patch_sensor_entities(sensor_module) -> None:
    if getattr(sensor_module.SolarInverterSensor, "_solar_modbus_debug_patched", False):
        return

    # Remove raw duplicate/status-register entities that are now represented by
    # decoded status entities or the dedicated control entity.
    sensor_module.DESCRIPTION[:] = [
        description
        for description in sensor_module.DESCRIPTION
        if description.data_key not in {"r0", "r4300", "r4446"}
    ]

    original_sensor_attrs = getattr(sensor_module.SolarInverterSensor, "extra_state_attributes", None)
    original_native_value = sensor_module.SolarInverterSensor.native_value

    @property
    def sensor_value(self):
        data_key = self.entity_description.data_key
        raw = self.coordinator.data.get(data_key)
        if data_key in STATUS_ENTITIES and raw is not None:
            _, status_map = STATUS_ENTITIES[data_key]
            raw_value = int(raw)
            if data_key == "r1023":
                return "No Fault" if raw_value == 0 else "Fault"
            return status_map.get(raw_value, f"Unknown ({raw_value})")
        return original_native_value.fget(self)

    @property
    def sensor_attrs(self):
        base = original_sensor_attrs.__get__(self) if original_sensor_attrs else {}
        result = dict(base or {})
        info = _raw_register_info(self.entity_description.data_key)
        if info:
            result.update(_attrs(*info))
        raw = self.coordinator.data.get(self.entity_description.data_key)
        if self.entity_description.data_key in STATUS_ENTITIES and raw is not None:
            result["raw_value"] = int(raw)
        return result

    sensor_module.SolarInverterSensor.native_value = sensor_value
    sensor_module.SolarInverterSensor.extra_state_attributes = sensor_attrs
    sensor_module.SolarInverterSensor._solar_modbus_debug_patched = True

    original_derived_attrs = getattr(sensor_module.SolarDerivedSensor, "extra_state_attributes", None)
    derived_sources = {
        "work_status_text": ("FC04", 0, "0-0", "r0"),
        "total_pv_power": ("FC04", 29, "29,32,35,38", "r29+r32+r35+r38"),
        "total_grid_power": ("FC04", 1078, "1078-1083", "r1078-r1083"),
        "total_inverter_power": ("FC04", 74, "74-76", "r74-r76"),
        "load_power": ("derived", 0, "derived", "total_inverter_power + total_grid_power"),
    }

    @property
    def derived_attrs(self):
        base = original_derived_attrs.__get__(self) if original_derived_attrs else {}
        result = dict(base or {})
        info = derived_sources.get(self._data_key)
        if info:
            result.update(_attrs(*info))
        return result

    sensor_module.SolarDerivedSensor.extra_state_attributes = derived_attrs

    load_cls = getattr(sensor_module, "SolarLoadEnergyTodaySensor", None)
    if load_cls:
        original_load_attrs = getattr(load_cls, "extra_state_attributes", None)

        @property
        def load_attrs(self):
            base = original_load_attrs.__get__(self) if original_load_attrs else {}
            result = dict(base or {})
            result.update(_attrs("FC04", 2056, "2056-2057", "Load Energy Use Total"))
            return result

        load_cls.extra_state_attributes = load_attrs

    ems_cls = getattr(sensor_module, "SolarInverterEmsModeSensor", None)
    if ems_cls:
        original_ems_attrs = getattr(ems_cls, "extra_state_attributes", None)

        @property
        def ems_attrs(self):
            base = original_ems_attrs.__get__(self) if original_ems_attrs else {}
            result = dict(base or {})
            value = self.coordinator.data.get("ems_mode")
            if value is not None:
                result["raw_value"] = int(value)
            result.update(_attrs("FC03", 4300, "4300-4300"))
            return result

        ems_cls.extra_state_attributes = ems_attrs
