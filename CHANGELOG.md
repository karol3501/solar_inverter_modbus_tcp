# Changelog

## 0.8.3

### Fixed
- Fixed `Load Energy Today` timezone handling for Home Assistant 2026.9+ by calling `dt_util.now()` without passing `HomeAssistant` as the timezone argument.
- Prevented `TypeError: tzinfo argument must be None or of a tzinfo subclass, not type 'HomeAssistant'` during coordinator listener updates.

## 0.8.2

### Fixed
- Fixed the FC04 energy telemetry read range: register 2068 is an I32 value and requires register 2069 for its low word.
- Prevented `KeyError: 'r2069'` during coordinator updates.

## 0.8.1

### Fixed
- Added the missing Grid Frequency entity from the original YAML configuration (register 66, scale 0.01 Hz).
- Preserved the existing inverter, backup, grid reactive-power, and PV-inverter meter entities while completing the YAML migration.

## 0.8.0

### Added
- Added all active Modbus telemetry from the original YAML configuration to the custom integration.
- Added derived sensors previously implemented as YAML template sensors: Work Status Text, Total PV Power, Total Grid Power, Total Inverter Power, and Load Power.
- Added persistent daily Load Energy Today based on Load Energy Use Total.
- Added Peak Shaving Baseline SOC and Peak Shaving Reserved SOC number controls for register 4446.
- Added the original PV, battery, grid, inverter, backup, BMS, diagnostic, energy-total, and daily-energy entities to the single Solar Inverter device.
- Preserved existing signed I16/I32 decoding and grid active-power direction handling.

## 0.7.5

### Added
- Added HACS installation badges and a direct **My Home Assistant** repository button to the README.
- Added a short HACS installation and configuration guide to the README.
- Added automated HACS validation through GitHub Actions.

## 0.7.4

### Fixed
- Fixed signed I32 telemetry handling: grid reactive power and PV inverter active power are no longer incorrectly re-decoded as signed 16-bit values.
- Applied the YAML `scale: -1` direction to grid active power registers 1078, 1080, and 1082 at the sensor layer, while keeping coordinator I32 values raw and signed.
- Preserved signed I16 decoding for PV currents, inverter currents/powers/reactive powers, and backup currents/powers/reactive powers.

## 0.7.3

### Fixed
- Fixed signed I16 decoding for PV, inverter, and backup current/power/reactive-power registers.
- Applied the correct `0.1` scale to PV, grid, inverter, and backup voltage registers.
- Applied the correct `0.01` scale to PV/inverter/backup currents.
- Applied the correct `0.01` scale to grid frequency register 66.
- Applied the YAML `scale: -1` direction to grid active power registers 1078, 1080, and 1082.
- Applied the correct `0.1` scale to battery voltage and `0.01` scale to battery current.

## 0.7.2

### Added
- Added integration icon at `custom_components/solar_inverter_modbus_tcp/brand/icon.png` for Home Assistant branding.

### Fixed
- Fixed Modbus FC04 read range for the sparse meter I32 values at registers 1078-1094 by reading through register 1095.
- Fixed I32 decoding of the final meter value at register 1094.
