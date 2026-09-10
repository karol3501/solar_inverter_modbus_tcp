# Changelog

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
