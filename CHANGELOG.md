# Changelog

## 0.9.0-dev2

### Added
- Added a **Reconfigure** action to the integration menu for changing the Modbus TCP host, port, and Unit ID without deleting and adding the integration again.
- Added connection validation before applying reconfigured Modbus TCP settings.

### Improved
- Reconfigure keeps the existing integration entry and reloads it automatically after a successful connection test.

## 0.9.0-dev1

### Added
- Added optional Modbus debug logging that can be enabled during initial setup or later from the integration Configure menu.
- Added detailed Modbus diagnostics for FC03/FC04 reads, including function code, address, register range, attempt number, response size, returned register values and request duration.
- Added detailed diagnostics for EMS FC16 writes and Peak Shaving FC06 writes, including verification requests.
- Added explicit error and retry messages with the exact Modbus address and register range that failed.
- Added Modbus metadata to entity state attributes so diagnostic entities expose their function code, address and register range.
- Added options for debug logging and polling interval without removing/re-adding the integration.

### Improved
- Added coordinator update timing and request-count diagnostics when debug logging is enabled.
- Kept debug logging disabled by default so normal Home Assistant logs remain quiet.

## 0.8.5

### Fixed
- Validated the Modbus TCP port before attempting a connection and rejected empty host values in the config flow.
- Kept Modbus connection validation errors user-facing without emitting a full exception traceback for normal connection failures.
- Retained the shared Modbus I/O lock and controlled FC03/FC04 retry handling introduced for intermittent timeout recovery.

### Improved
- Improved config-flow input handling for invalid Unit ID values.

## 0.8.4

### Fixed
- Serialized all Modbus TCP reads and writes through a shared lock so coordinator polling cannot overlap with EMS or Peak Shaving control operations.
- Added one controlled retry for failed FC03/FC04 reads to recover from transient Modbus timeouts or connection drops without immediately aborting the update cycle.
- Added retry diagnostics identifying the exact Modbus register range that failed.
- Hardened CI validation and the automatic release workflow.

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
