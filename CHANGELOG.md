# Changelog

## 1.0.6

### Fixed
- Fixed Reconfigure to update the Config Entry unique ID when the Modbus TCP connection changes, reject duplicate connections, and reload the integration only once.
- Assigned inverter entities to a separate Home Assistant device for each Config Entry.
- Assigned each detected EV charger to its own Home Assistant device, identified by its serial number.
- Preserved the raw **BMS Fault Code** as the `raw_code` attribute and standardized link-state labels to `Connected` / `Disconnected`.
- Updated Number entity state only after a successful Modbus write and prevented invalid EV charger detection when the serial number is absent.
- Added Polish translations and regression-test workflow coverage.


## 1.0.5

### Fixed
- Fixed the **Connect solar inverter** and **Reconfigure solar inverter** form ordering so the optional settings are presented consistently, with **Debug logging** at the bottom.
- Added missing translations and descriptions for **Polling interval**, **Generator**, **EV chargers**, and **Debug logging** in the Reconfigure and Options flows.
- Fixed the Reconfigure completion message by adding the required **reconfigure_successful** translation, preventing the Home Assistant flow from ending with an unknown error.

## 1.0.4

### Fixed
- Fixed **BMS Link Status** to show `connected` or `disconnected` instead of the raw Modbus value.
- Fixed **Grid Meter Link Status** to show `connected` or `disconnected` instead of the raw Modbus value.

## 1.0.3

### Fixed
- Fixed the initial setup form so **Polling interval** is saved from the selected value instead of always falling back to 10 seconds.
- Unified the initial setup and Reconfigure options so the same polling configuration is available in both flows.

## 1.0.2

### Fixed
- Fixed **Load Energy Today** resetting to zero after an integration reload by correctly restoring the saved daily baseline before calculating the sensor value.
- Preserved the daily baseline and reset date across Home Assistant integration reloads.

## 1.0.1

### Fixed
- Fixed Reconfigure so all integration options are available alongside the Modbus TCP connection settings.
- Fixed EV charger detection by validating connection status, communication address, and serial number instead of relying on a single status register.
- Re-run EV charger detection during reconfiguration so only detected chargers are enabled.

## 1.0.0

### Added
- Added optional Generator telemetry with all documented generator voltage, current, active power, and daily energy entities.
- Added optional EV Charger telemetry for EV Charger 1 and EV Charger 2 using the documented charger register blocks.
- Added automatic EV charger detection when EV chargers are enabled; only detected chargers create entities and their register blocks are polled.
- Added EV charger detection information during initial configuration.

### Changed
- Removed the raw Work Status entity; register `r0` is used internally for the calculated human-readable Work Status entity.
- Removed the duplicate base Generator Energy Today entity so generator energy is only exposed when Generator telemetry is enabled.
- Kept Generator and EV Charger telemetry conditional on their configuration options.

### Removed
- Removed the obsolete Grid Reactive Power registers from polling and decoding.
- Removed obsolete Modbus function/register/source attributes from entity state attributes.

## 0.9.10

### Changed
- Removed the obsolete debug attribute patching module and its startup hook.
- Standardized Peak Shaving number entity attributes to remove Modbus function and register-range metadata.
- Standardized EMS Mode Control attributes to remove Modbus function, register-range, and verification metadata.
- Removed unused Grid Reactive Power registers (`r1084`, `r1086`, `r1088`) from polling and 32-bit decoding.
- Removed obsolete `r2070` Load Energy Total polling and decoding because the entity was already removed.
- Removed obsolete internal aliases for direct aggregate registers `r26`, `r73`, and `r91`.

### Removed
- Removed obsolete `debug_attributes.py`.
- Removed duplicate `brand/icon1.png`.
- Removed Grid Reactive Power L1-L3 (`r1084`, `r1086`, `r1088`) from Modbus polling.

## 0.9.9

### Changed
- Standardized sensor attributes for direct Modbus sensors: Device class, Friendly name, State class, Unit of measurement, and Modbus address.
- Standardized calculated sensor attributes: Device class, Friendly name, State class, Unit of measurement, `calculated: true`, and `source_sensors`.
- Removed Modbus function, Modbus registers, and Modbus source attributes from sensor entities.
- Removed calculation text from calculated sensor attributes.
- Kept Load Energy Today as a calculated sensor based on Load Energy Use Total (`r2056`).

## 0.9.7

### Changed
- Fixed Load Power calculation for positive and negative Total Inverter Power and Total Grid Power by using `abs(Total Inverter Power + Total Grid Power)`.
- Kept Load Energy Today as a calculated sensor based on Load Energy Use Total (`r2056`).
- Converted Total PV Power to a calculated sensor based on PV1-PV4 Power (`r29`, `r32`, `r35`, `r38`).
- Converted Total Grid Power to a calculated sensor based on Grid Active Power L1-L3 (`r1078`, `r1080`, `r1082`).
- Converted Total Inverter Power to a calculated sensor based on Inverter Active Power L1-L3 (`r74`, `r75`, `r76`).
- Converted Backup Active Power to a calculated sensor based on Backup Active Power A-C (`r92`, `r93`, `r94`).
- Calculated sensors now expose only `calculated` and `source_sensors` as custom attributes.
- Direct Modbus sensors now expose only `modbus_address` as their Modbus custom attribute.
- Removed Modbus function/register metadata from all sensor attributes.

### Removed
- Removed Load Energy Total (`r2070`).
- Removed Grid Reactive Power L1-L3 (`r1084`, `r1086`, `r1088`).
- Removed direct Modbus entities for Total PV Power (`r26`), Inverter Active Power (`r73`), and Backup Active Power (`r91`); their values are calculated from phase/channel sensors.

## 0.9.6

### Changed
- Converted Total PV Power to a calculated sensor based on PV1-PV4 Power (`r29`, `r32`, `r35`, `r38`).
- Converted Total Inverter Power to a calculated sensor based on Inverter Active Power L1-L3 (`r74`, `r75`, `r76`).
- Converted Backup Active Power to a calculated sensor based on Backup Active Power A-C (`r92`, `r93`, `r94`).
- Added calculated-sensor attributes describing source sensors and the calculation used.
- Calculated sensors no longer expose Modbus address/function metadata because they are not direct Modbus sensors.

### Removed
- Removed Load Energy Total (`r2070`).
- Removed Grid Reactive Power L1-L3 (`r1084`, `r1086`, `r1088`).
- Removed direct Modbus entities for Total PV Power (`r26`), Inverter Active Power (`r73`), and Backup Active Power (`r91`); their values are now calculated from phase/channel sensors.

## 0.9.5

### Fixed
- Fixed Ruff `RUF100` validation in the Peak Shaving Modbus recovery handler.

## 0.9.4

### Fixed
- Added a 250 ms gap between Modbus transactions to match the previous working communication pacing and avoid overloading the inverter TCP endpoint.
- Recycle the shared Modbus connection after timeout/connection-loss errors so the next request can establish a fresh TCP connection.
- Stop the current polling cycle after a connection-level failure instead of sending the remaining requests into a wedged connection.
- Added the same pacing and connection recovery to Peak Shaving FC06 writes on register `4446`.

## 0.9.3

### Fixed
- Removed the unused `noqa` directive from the Peak Shaving write exception handler so Ruff `RUF100` passes cleanly.

## 0.9.2

### Fixed
- Fixed **Peak Shaving** controls so the Home Assistant entity value updates immediately after a user change.
- Removed the extra FC03 read and FC03 verification read from the Peak Shaving write path when the latest register `4446` value is already available from the coordinator.
- Peak Shaving now updates the packed register state optimistically before the FC06 write, while the next coordinator poll confirms the actual inverter value.
- Kept Baseline SOC in the high byte and Reserved SOC in the low byte of register `4446`.

## 0.9.1

### Fixed
- Changed **BMS Fault Code** register `1023` to a readable status: `0` → **No Fault**, any other value → **Fault**.
- Preserved the original numeric register value as the `raw_code` entity attribute for diagnostics.

## 0.9.0-dev5

### Added
- Added raw **HW Fault** register `21` as a 32-bit value (`21-22`).
- Added **PV Total Power** from register `26`.
- Added **Grid Meter Voltage L1-L3** from registers `1047-1049`.
- Added **Load Energy Total** from register `2070`, while keeping the existing `Load Energy Use Total` register `2056` for comparison.
- Added **Energy From PV Today** from register `2132`.

### Changed
- Updated Work Status text mapping to: `Initialising`, `Standby`, `Grid Check`, `Fault`, `Grid Off`, `Bypass`, `PV Charging Battery`, `Generator Mode`, and `Island Mode`.
- Kept **Safety DSP FM Version** register `201`.
- Kept **DRM Status** register `1060` as raw numeric data without an invented enum mapping.
- Kept **BMS Fault Code** register `1023` as raw numeric data.
- Renamed the Grid Meter link entity to **Grid Meter Link Status**.
- Renamed the derived Work Status entity from **Work Status Text** to **Work Status**.
- Split the large FC04 telemetry range into smaller Battery, Inverter, Backup, Grid Meter, and energy blocks so a failed range does not stop unrelated entities from updating.
- Extended the energy block to include register `2070`.

### Removed
- Removed ReConnect Counter `210`.
- Removed PE/PF Voltage `241`.
- Removed Iso Resistor `242`.
- Removed Residual Current `243`.
- Removed Inverter Reactive Power `77-80`.
- Removed Backup Current `84-86`.
- Removed Backup Apparent Power `87-90`.
- Removed PV Inverter Active Power A-C `1090`, `1092`, `1094`.

## 0.9.0-dev4

### Improved
- Marked the development build explicitly as `0.9.0-dev4` so the manifest and development branch version stay synchronized.
- Continued the status cleanup work from the previous development build: normal status entities use readable states where the Modbus mapping is verified, while raw values remain available through diagnostic attributes.
- Kept DRM register 1060 out of an invented Active/Inactive mapping until an authoritative register enum is confirmed.

### Fixed
- Corrected the development version mismatch where the DEV branch manifest still reported `0.9.0`.

## 0.9.0

### Added
- Added optional Modbus debug logging that can be enabled during initial setup or later from the integration Configure menu.
- Added detailed Modbus diagnostics for FC03/FC04 reads, including function code, address, register range, attempt number, response size, returned register values and request duration.
- Added detailed diagnostics for EMS FC16 writes and Peak Shaving FC06 writes, including verification requests.
- Added explicit error and retry messages with the exact Modbus address and register range that failed.
- Added Modbus metadata to entity state attributes so diagnostic entities expose their function code, address and register range.
- Added options for debug logging and polling interval without removing/re-adding the integration.
- Added a **Reconfigure** action to the integration menu for changing the Modbus TCP host, port, and Unit ID without deleting the integration again.

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
