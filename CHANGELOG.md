# Changelog

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
