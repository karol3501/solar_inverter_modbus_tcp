# Solar Inverter Modbus TCP

Custom Home Assistant integration for solar inverters using Modbus TCP.

## Current status — 0.6.3

Minimal working integration focused on EMS Mode:

- Modbus TCP connection
- Config flow with Host, Port and Unit ID
- Connection validation using FC03 register `4300`
- EMS Mode sensor from holding register `4300`
- EMS Mode control via FC06 write to register `4300`
- Immediate read-back verification after writes
- Uses Home Assistant's modern `async_get_unit` / `async_get_temporary_unit` Modbus API
- Custom green/blue circular integration logo

## EMS modes

| Value | Mode |
|---:|---|
| 0 | Self-Use |
| 1 | Economical Mode |
| 2 | Backup Mode |
| 3 | Pure Off-Grid Mode |
| 4 | Force Charge Mode |
| 5 | Force Discharge Mode |
| 6 | Peak-shaving Mode |
| 7 | TOU Mode |

Register `4300` is an EMS Mode register used by the supported inverter protocol.

## Roadmap

The next stages will add grouped telemetry for PV, grid, battery, load, energy and BMS.

## Installation

The integration is intended for HACS and manual installation into:

`/config/custom_components/solar_inverter_modbus_tcp/`

## Protocol

The integration uses Modbus TCP and is designed around a generic solar-inverter register model. Device-specific register definitions will be added as supported models are validated.
