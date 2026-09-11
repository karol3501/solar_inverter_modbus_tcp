# Changelog

## 0.9.0

### Added
- Added optional Modbus debug logging that can be enabled during initial setup or later from the integration Configure menu.
- Added detailed Modbus diagnostics for FC03/FC04 reads, including function code, address, register range, attempt number, response size, returned register values and request duration.
- Added detailed diagnostics for EMS FC16 writes and Peak Shaving FC06 writes, including verification requests.
- Added explicit error and retry messages with the exact Modbus address and register range that failed.
- Added Modbus metadata to entity state attributes so diagnostic entities expose their function code, address and register range.
- Added options for debug logging and polling interval without removing/re-adding the integration.
- Added a **Reconfigure** action to the integration menu for changing the Modbus TCP host, port, and Unit ID without deleting and adding the integration again.

### Improved
- Added coordinator update timing and request-count diagnostics when debug logging is enabled.
- Kept debug logging disabled by default so normal Home Assistant logs remain quiet.
- Added connection validation before applying reconfigured Modbus TCP settings.
- Reconfigure keeps the existing integration entry and reloads it automatically after a successful connection test.
- Improved Modbus update resilience by keeping the last good data for individual register blocks when a single read fails.
- Prevented one failed telemetry block from stopping fresh data updates for all other entities.
- Kept exact Modbus function, address, and register-range diagnostics for failed blocks.
- Replaced raw numeric status entities with human-readable states for Work Status, BMS Link Status, BMS Fault Status, Grid Meter Link Status, and EMS Mode.
- Removed duplicate raw EMS/Peak Meter SOC entities from the normal entity list; their raw register values remain available as entity attributes for diagnostics.
- Added `raw_value` attributes to decoded status entities so the original Modbus value remains available for troubleshooting.
- Set Battery Voltage display precision to 1 decimal place so values such as `51.0 V` are shown instead of `51 V`.

### Fixed
- Prevented unverified DRM register `1060` values from being presented as `Active/Inactive`; the integration now keeps the raw DRM value until an authoritative Modbus mapping is available.

## 0.8.5

### Fixed
- Validated the Modbus TCP port before attempting a connection and rejected empty host values in the config flow.
- Kept Modbus connection validation errors user-facing without emitting a full exception traceback for normal connection failures.
- Retained the shared Modbus I/O lock and controlled FC03/FC04 retry handling introduced for intermittent timeout recovery.

### Improved
- Improved config-flow input handling for invalid Unit ID values.

## 0.8.4

### Fixed
- Added a shared Modbus I/O lock so coordinator polling and write operations cannot overlap on the same TCP connection.
- Added controlled retry handling for intermittent FC03/FC04 timeouts and connection drops.

### Improved
- Added clearer Modbus error logging with function code and register range information.

## 0.8.3

### Added
- Added local Home Assistant branding assets (`brand/icon.png` and `brand/logo.png`) for HA 2026.3+.

## 0.8.2

### Improved
- Updated the integration for the new Home Assistant 2026.9 Modbus connection API using `async_get_unit` and `async_get_temporary_unit`.
- Removed use of the deprecated `modbus.get_hub` API.

## 0.8.1

### Fixed
- Fixed Modbus TCP connection setup and validation with the new Home Assistant Modbus API.

## 0.8.0

### Added
- Added support for the new Home Assistant Modbus connection API.
- Added a shared coordinator for all inverter data.
- Added EMS mode selection and Peak Shaving configuration.

## 0.7.2

### Fixed
- Fixed entity naming and state-class handling for Home Assistant energy sensors.
