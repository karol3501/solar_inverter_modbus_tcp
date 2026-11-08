"""Isolated regression tests for polling, platform setup and entity migration.

Run with python -m unittest discover -s tests. These tests execute the relevant
source definitions with fake HA and Modbus boundaries, using only the stdlib.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import os
from pathlib import Path
from types import SimpleNamespace
import unittest


ROOT = Path(os.environ.get('SOLAR_TEST_ROOT', Path(__file__).resolve().parents[1]))
COMPONENT = ROOT / 'custom_components/solar_inverter_modbus_tcp'
DOMAIN = 'solar_inverter_modbus_tcp'


def load_definitions(filename, names, namespace):
    """Execute selected real definitions while replacing external boundaries."""
    tree = ast.parse((COMPONENT / filename).read_text(encoding='utf-8'))
    definitions = [node for node in tree.body if getattr(node, 'name', None) in names]
    assert len(definitions) == len(names)
    module = ast.Module(
        body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *definitions],
        type_ignores=[],
    )
    exec(compile(ast.fix_missing_locations(module), filename, 'exec'), namespace)
    return namespace


class PollingTests(unittest.IsolatedAsyncioTestCase):
    def make_coordinator(self, *, enabled=False, chargers=None, status=1, address=1, serial=123, fail_detection=False, fail_all=False):
        class FakeCoordinatorBase:
            def __class_getitem__(cls, item):
                return cls

        namespace = load_definitions('coordinator.py', {
            '_i16', '_i32', '_u32', '_u64', '_put_block', '_is_connection_error', 'SolarInverterCoordinator',
        }, {'DataUpdateCoordinator': FakeCoordinatorBase, 'UpdateFailed': RuntimeError, '_LOGGER': logging.getLogger(__name__)})
        coordinator = namespace['SolarInverterCoordinator'].__new__(namespace['SolarInverterCoordinator'])
        coordinator.enable_generator = False
        coordinator.enable_ev_charger = enabled
        coordinator.ev_chargers = chargers
        coordinator._last_data = {}
        calls = []

        async def read_input(start, count):
            calls.append(('input', start, count))
            if fail_all or (fail_detection and start == 3200):
                raise RuntimeError('illegal address')
            registers = {3200: status, 3201: address, 3205: serial, 2068: 1, 2069: 2}
            return [registers.get(register, 0) for register in range(start, start + count)]

        async def read_holding(start, count):
            calls.append(('holding', start, count))
            if fail_all:
                raise RuntimeError('illegal address')
            return [0] * count

        coordinator._read_input = read_input
        coordinator._read_holding = read_holding
        return coordinator, calls

    async def test_detects_ev_from_empty_cache(self):
        coordinator, calls = self.make_coordinator(enabled=True)
        data = await coordinator._async_update_data_locked()
        self.assertEqual(coordinator.ev_chargers, (1,))
        self.assertEqual(data['r3205'], 123)
        self.assertIn(('input', 3200, 25), calls)
        self.assertIn(('holding', 4700, 5), calls)

    async def test_invalid_ev_identity_is_rejected(self):
        for values in ({'status': 0}, {'address': 0}, {'address': 248}, {'serial': 0}, {'fail_detection': True}):
            with self.subTest(values=values):
                coordinator, calls = self.make_coordinator(enabled=True, **values)
                await coordinator._async_update_data_locked()
                self.assertEqual(coordinator.ev_chargers, ())
                self.assertNotIn(('holding', 4700, 5), calls)

    async def test_ev_address_boundaries(self):
        for address in (1, 247):
            with self.subTest(address=address):
                coordinator, _ = self.make_coordinator(enabled=True, address=address)
                await coordinator._async_update_data_locked()
                self.assertEqual(coordinator.ev_chargers, (1,))

    async def test_disabled_ev_is_not_polled(self):
        coordinator, calls = self.make_coordinator()
        await coordinator._async_update_data_locked()
        self.assertFalse(any(start == 3200 for _, start, _ in calls))

    async def test_saved_ev_list_skips_detection(self):
        coordinator, calls = self.make_coordinator(enabled=True, chargers=(1,))
        await coordinator._async_update_data_locked()
        self.assertNotIn(('input', 3200, 6), calls)
        self.assertIn(('input', 3200, 25), calls)

    async def test_grid_to_load_energy_uses_both_words(self):
        coordinator, _ = self.make_coordinator()
        data = await coordinator._async_update_data_locked()
        self.assertEqual(data['r2069_raw'], 2)
        self.assertEqual(data['r2068'], 65538)

    async def test_all_failed_reads_raise(self):
        coordinator, _ = self.make_coordinator(fail_all=True)
        with self.assertRaisesRegex(RuntimeError, 'all .* requests failed'):
            await coordinator._async_update_data_locked()


class PlatformSetupTests(unittest.IsolatedAsyncioTestCase):
    async def test_platforms_accept_missing_empty_and_populated_ev_lists(self):
        for filename, expected_without_ev in (('number.py', 17), ('select.py', 1)):
            for chargers, extra in ((None, 0), ((), 0), ((1,), 3 if filename == 'number.py' else 2)):
                with self.subTest(filename=filename, chargers=chargers):
                    namespace = {name: lambda *args: object() for name in (
                        'PeakShavingNumber', 'ExportPowerLimitNumber', 'BatterySettingNumber',
                        'EmsSettingNumber', 'EvChargerPowerNumber', 'SolarInverterEmsSelect', 'EvChargerSettingSelect',
                    )}
                    namespace['NumberMode'] = SimpleNamespace(SLIDER='slider')
                    load_definitions(filename, {'async_setup_entry'}, namespace)
                    added = []
                    entry = SimpleNamespace(runtime_data=SimpleNamespace(ev_chargers=chargers, ev_charger_rated_power_kw=11))
                    await namespace['async_setup_entry'](None, entry, added.extend)
                    self.assertEqual(len(added), expected_without_ev + extra)


class MigrationTests(unittest.TestCase):
    def migrate(self, entity_id, *, key='total_grid_power', target_taken=False):
        changes = []
        target = 'sensor.solar_inverter_grid_active_power' if key == 'total_grid_power' else 'sensor.ev_charger_status'
        unique_id = f'{DOMAIN}_entry_{key}'
        registry = SimpleNamespace(
            async_get_entity_id=lambda *args: entity_id if args[-1] == unique_id else None,
            async_get=lambda candidate: object() if target_taken and candidate == target else None,
            async_update_entity=lambda *args, **kwargs: changes.append((args, kwargs)),
        )
        namespace = load_definitions('__init__.py', {'_async_migrate_sensor_entity_ids'}, {
            'er': SimpleNamespace(async_get=lambda hass: registry),
            'DOMAIN': DOMAIN,
            'EV_CHARGER_DESCRIPTION': [SimpleNamespace(key='r3212', name='EV Charger Status')],
            'slugify': lambda value: value.lower().replace(' ', '_'),
            '_LOGGER': logging.getLogger(__name__),
        })
        namespace['_async_migrate_sensor_entity_ids'](None, SimpleNamespace(entry_id='entry'))
        return changes

    def test_custom_entity_ids_are_preserved(self):
        for key in ('total_grid_power', 'r3212'):
            with self.subTest(key=key):
                self.assertEqual(self.migrate('sensor.my_custom_name', key=key), [])

    def test_known_legacy_ids_are_migrated(self):
        for key, source, target in (
            ('total_grid_power', 'sensor.solar_inverter_total_grid_power', 'sensor.solar_inverter_grid_active_power'),
            ('r3212', 'sensor.solar_inverter_ev_charger_status', 'sensor.ev_charger_status'),
        ):
            with self.subTest(key=key):
                self.assertEqual(self.migrate(source, key=key), [((source,), {'new_entity_id': target})])

    def test_occupied_targets_are_preserved(self):
        self.assertEqual(self.migrate('sensor.solar_inverter_total_grid_power', target_taken=True), [])

    def test_missing_and_already_migrated_entities_are_skipped(self):
        for entity_id in (None, 'sensor.solar_inverter_grid_active_power'):
            with self.subTest(entity_id=entity_id):
                self.assertEqual(self.migrate(entity_id), [])

    def test_suffixed_entity_id_is_preserved(self):
        self.assertEqual(self.migrate('sensor.solar_inverter_total_grid_power_2'), [])


if __name__ == '__main__':
    unittest.main()
