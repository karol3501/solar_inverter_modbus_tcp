# Solar Inverter Modbus TCP

Custom Home Assistant integration for solar inverters using Modbus TCP.

[![Open HACS Repository on My Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=karol3501&repository=solar_inverter_modbus_tcp&category=integration)
[![Latest Release](https://img.shields.io/github/v/release/karol3501/solar_inverter_modbus_tcp?style=flat&label=release)](https://github.com/karol3501/solar_inverter_modbus_tcp/releases)
[![HACS Validation](https://github.com/karol3501/solar_inverter_modbus_tcp/actions/workflows/hacs.yml/badge.svg)](https://github.com/karol3501/solar_inverter_modbus_tcp/actions/workflows/hacs.yml)
[![License](https://img.shields.io/github/license/karol3501/solar_inverter_modbus_tcp?style=flat)](https://github.com/karol3501/solar_inverter_modbus_tcp/blob/main/LICENSE)

## Installation via HACS

### Option 1 — One click

Click the button above:

**Open HACS Repository on My Home Assistant**

HACS will open the repository page and allow you to install the integration.

### Option 2 — Add as a custom repository

If the button does not work:

1. Open **HACS** in Home Assistant.
2. Go to **Integrations**.
3. Click the **⋮** menu in the top-right corner.
4. Select **Custom repositories**.
5. Enter:
   ```text
   https://github.com/karol3501/solar_inverter_modbus_tcp
   ```
6. Select **Integration** as the category.
7. Click **Add**.
8. Search for **Solar Inverter Modbus TCP** in HACS and install it.
9. Restart Home Assistant.

## Configuration

After installation:

1. Open **Settings → Devices & services**.
2. Click **Add Integration**.
3. Search for **Solar Inverter Modbus TCP**.
4. Enter the Modbus TCP connection parameters:
   - **Host** — IP address of the inverter
   - **Port** — normally `502`
   - **Unit ID** — Modbus slave/unit ID, normally `1`
5. Finish the setup.

The integration creates a single Home Assistant device and exposes the supported inverter telemetry and controls through that device.

## Updates

Updates are delivered through HACS. After a new release is published, HACS will show the available update in Home Assistant.

The repository uses GitHub Releases and the integration version from `custom_components/solar_inverter_modbus_tcp/manifest.json`.

## Development

Every integration change should increment the version according to the project's versioning policy and include an entry in `CHANGELOG.md`.

## License

MIT License.
