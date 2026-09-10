# Hoymiles HIT-10L-G3 Modbus TCP

Custom Home Assistant integration for the Hoymiles HIT-10L-G3 hybrid inverter over Modbus TCP.

## Current status — 0.6.1

Minimal working integration focused on EMS Mode:

- Modbus TCP connection
- Config flow with Host, Port and Unit ID
- Connection/device validation using FC03 register `4300`
- EMS Mode sensor from holding register `4300`
- EMS Mode control via FC06 write to register `4300`
- Immediate read-back verification after writes
- Uses Home Assistant's modern `async_get_unit` / `async_get_temporary_unit` Modbus API

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

Register `4300` is documented by Hoymiles as EMS Mode (RW U16).

## Roadmap

The next stages will add grouped telemetry for PV, grid, battery, load, energy and BMS, based on the official Hoymiles Modbus documentation and the verified Home Assistant YAML configuration.

## Installation

The integration is intended for HACS and manual installation into:

`/config/custom_components/hoymiles_hit_10l_g3/`

## Credits / references

Protocol implementation is based on the official Hoymiles Energy Storage Modbus documentation and verified against a working HIT-10L-G3 Modbus TCP installation.
