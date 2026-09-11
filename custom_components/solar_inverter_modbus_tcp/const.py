DOMAIN = "solar_inverter_modbus_tcp"
DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1
CONF_UNIT_ID = "unit_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_DEBUG_LOGGING = "debug_logging"

EMS_MODES = {
    0: "Self-Use",
    1: "Economical Mode",
    2: "Backup Mode",
    3: "Pure Off-Grid Mode",
    4: "Force Charge Mode",
    5: "Force Discharge Mode",
    6: "Peak-shaving Mode",
    7: "TOU Mode",
}
