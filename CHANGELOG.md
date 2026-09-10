# Changelog

## 0.7.2

### Added
- Added integration icon at `custom_components/solar_inverter_modbus_tcp/brand/icon.png` for Home Assistant branding.

### Fixed
- Fixed Modbus FC04 read range for the sparse meter I32 values at registers 1078-1094 by reading through register 1095.
- Fixed I32 decoding of the final meter value at register 1094.
