"""Connection metrics cover real requests and remain visible during outages."""

from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

import test_control_writes
from test_control_writes import FakeEntity, make_coordinator
from test_review_regressions import load_definitions


class RequestDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_read_records_utc_timestamp_and_response_time(self):
        coordinator = make_coordinator()
        coordinator.unit.read_holding_registers = AsyncMock(return_value=[42])
        namespace = coordinator.async_modbus_request.__func__.__globals__
        namespace['time'] = SimpleNamespace(monotonic=Mock(side_effect=[10, 10.125]))
        result = await coordinator.async_modbus_request('read_holding_registers', 259, 1)
        self.assertEqual(result, [42])
        self.assertEqual(coordinator.response_time_ms, 125)
        self.assertEqual(coordinator.last_successful_read.tzinfo, timezone.utc)
        self.assertEqual(coordinator.timeout_count, 0)

    async def test_write_does_not_change_last_successful_read(self):
        coordinator = make_coordinator()
        await coordinator.async_modbus_request('write_register', 259, 42)
        self.assertIsNone(coordinator.last_successful_read)
        self.assertIsNotNone(coordinator.response_time_ms)

    async def test_short_read_does_not_record_successful_read(self):
        coordinator = make_coordinator()
        coordinator.unit.read_holding_registers = AsyncMock(return_value=[42])
        await coordinator.async_modbus_request('read_holding_registers', 259, 2)
        self.assertIsNone(coordinator.last_successful_read)

    async def test_timeout_keeps_last_success_and_counts_each_attempt(self):
        coordinator = make_coordinator()
        timestamp = datetime.now(timezone.utc)
        coordinator.last_successful_read = timestamp
        coordinator.response_time_ms = 123
        coordinator.unit.read_holding_registers = AsyncMock(side_effect=TimeoutError())
        for _ in range(2):
            with self.assertRaises(TimeoutError):
                await coordinator.async_modbus_request('read_holding_registers', 259, 1)
        self.assertEqual(coordinator.timeout_count, 2)
        self.assertEqual(coordinator.last_successful_read, timestamp)
        self.assertEqual(coordinator.response_time_ms, 123)

    async def test_library_timeout_message_is_counted(self):
        coordinator = make_coordinator()
        coordinator.unit.write_register.side_effect = RuntimeError('Response timeout after 10.0 seconds')
        with self.assertRaises(RuntimeError):
            await coordinator.async_modbus_request('write_register', 4446, 15656)
        self.assertEqual(coordinator.timeout_count, 1)

    async def test_other_errors_do_not_increase_timeout_count(self):
        coordinator = make_coordinator()
        coordinator.unit.write_register.side_effect = ValueError('illegal address')
        with self.assertRaises(ValueError):
            await coordinator.async_modbus_request('write_register', 4446, 15656)
        self.assertEqual(coordinator.timeout_count, 0)

    async def test_recovered_timeout_still_counts(self):
        coordinator = make_coordinator()
        coordinator.unit.write_register.side_effect = TimeoutError('Response timeout')
        coordinator._read_holding.return_value = [15656]
        await coordinator.async_write_register(4446, 15656)
        self.assertEqual(coordinator.timeout_count, 1)

    async def test_verification_reads_are_measured_for_all_controls(self):
        # Use the real platform setters and coordinator request wrapper.
        fixture = test_control_writes.ImmediateFeedbackTests()
        coordinator, controls = fixture.make_controls()
        for entity, value in controls[2:]:
            with self.subTest(entity=type(entity).__name__):
                coordinator.last_successful_read = None
                await fixture.setter(entity)(value)
                self.assertIsNotNone(coordinator.last_successful_read)

    async def test_poll_read_retries_are_measured(self):
        coordinator = make_coordinator()
        coordinator.debug_logging = False
        coordinator.unit.read_input_registers = AsyncMock(side_effect=[TimeoutError('Response timeout'), [42]])
        result = await coordinator._read('FC04', 0, 1)
        self.assertEqual(result, [42])
        self.assertEqual(coordinator.timeout_count, 1)
        self.assertIsNotNone(coordinator.last_successful_read)
        self.assertIsNotNone(coordinator.response_time_ms)


class DiagnosticSensorTests(unittest.IsolatedAsyncioTestCase):
    def namespace(self):
        sensor = SimpleNamespace(
            SensorEntity=type('SensorEntity', (), {}),
            SensorDeviceClass=SimpleNamespace(TIMESTAMP='timestamp', DURATION='duration'),
            SensorStateClass=SimpleNamespace(MEASUREMENT='measurement', TOTAL_INCREASING='total_increasing'),
        )
        return load_definitions('sensor.py', {'SolarConnectionDiagnosticSensor', 'async_setup_entry'}, {
            'CoordinatorEntity': FakeEntity, 'SolarInverterCoordinator': object,
            'EntityCategory': SimpleNamespace(DIAGNOSTIC='diagnostic'), 'sensor': sensor,
            'DOMAIN': 'solar_inverter_modbus_tcp',
            'inverter_device_info': lambda coordinator: {'identifiers': {('solar_inverter_modbus_tcp', coordinator.entry_id)}},
            'DESCRIPTION': [], 'DERIVED': [],
            'SolarLoadEnergyTodaySensor': FakeEntity, 'SolarInverterEmsModeSensor': FakeEntity,
        })

    async def test_setup_adds_three_diagnostic_sensors(self):
        namespace = self.namespace()
        coordinator = SimpleNamespace(entry_id='entry', enable_generator=False, enable_ev_charger=False,
                                      last_successful_read=None, response_time_ms=None, timeout_count=0)
        added = []
        await namespace['async_setup_entry'](None, SimpleNamespace(runtime_data=coordinator), added.extend)
        diagnostics = added[2:]
        self.assertEqual(len(diagnostics), 3)
        self.assertEqual([entity.native_value for entity in diagnostics], [None, None, 0])
        self.assertEqual(diagnostics[0]._attr_device_class, 'timestamp')
        self.assertEqual(diagnostics[1]._attr_native_unit_of_measurement, 'ms')
        self.assertTrue(all(entity._attr_entity_category == 'diagnostic' for entity in diagnostics))
        self.assertTrue(all(entity.available for entity in diagnostics))
        self.assertEqual(len({entity._attr_unique_id for entity in diagnostics}), 3)
        coordinator.last_update_success = False
        coordinator.timeout_count = 7
        self.assertTrue(diagnostics[2].available)
        self.assertEqual(diagnostics[2].native_value, 7)

    async def test_unique_ids_are_scoped_to_config_entries(self):
        cls = self.namespace()['SolarConnectionDiagnosticSensor']
        first = cls(SimpleNamespace(entry_id='first'), 'timeout_count', 'Timeouts', None, None, None)
        second = cls(SimpleNamespace(entry_id='second'), 'timeout_count', 'Timeouts', None, None, None)
        self.assertNotEqual(first._attr_unique_id, second._attr_unique_id)


if __name__ == '__main__':
    unittest.main()
