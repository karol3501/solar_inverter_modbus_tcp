DOMAIN = "solar_inverter_modbus_tcp"
DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1
CONF_UNIT_ID = "unit_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_DEBUG_LOGGING = "debug_logging"
CONF_ENABLE_GENERATOR = "enable_generator"
CONF_ENABLE_EV_CHARGER = "enable_ev_charger"
CONF_EV_CHARGERS = "ev_chargers"
CONF_EV_CHARGER_1_RATED_POWER_KW = "ev_charger_1_rated_power_kw"
CONF_EV_CHARGER_2_RATED_POWER_KW = "ev_charger_2_rated_power_kw"
CONF_EXPORT_LIMIT_WATTS = "export_limit_watts"
CONF_INVERTER_RATED_POWER_WATTS = "inverter_rated_power_watts"

DEFAULT_EXPORT_LIMIT_WATTS = 1000
DEFAULT_INVERTER_RATED_POWER_WATTS = 10000
DEFAULT_EV_CHARGER_RATED_POWER_KW = 11.0

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

