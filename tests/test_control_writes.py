"""Regression tests for immediate control feedback and write recovery."""

import asyncio
from datetime import time as datetime_time
from datetime import datetime, timezone
import logging
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from functools import wraps

from test_review_regressions import load_definitions


class FakeCoordinatorBase:
    def __class_getitem__(cls, item):
        return cls

    def async_set_updated_data(self, data):
        self.data = data

    def async_update_listeners(self):
        pass


def make_coordinator():
    namespace = load_definitions('coordinator.py', {
        'SolarInverterCoordinator', '_is_connection_error',
    }, {
        'DataUpdateCoordinator': FakeCoordinatorBase,
        '_LOGGER': logging.getLogger(__name__),
        '_WRITE_RETRIES': 2, '_RETRY_DELAY': 0, '_INTER_REQUEST_DELAY': 0,
        '_READ_RETRIES': 2, 'UpdateFailed': RuntimeError,
        'asyncio': asyncio,
        'time': __import__('time'), 'datetime': datetime, 'timezone': timezone,
    })
    coordinator_type = namespace['SolarInverterCoordinator']
    coordinator = coordinator_type.__new__(coordinator_type)
    coordinator.unit = SimpleNamespace(
        write_register=AsyncMock(), write_registers=AsyncMock(), disconnect=AsyncMock(),
    )
    coordinator._read_holding = AsyncMock(return_value=[0])
    coordinator.timeout_count = 0
    coordinator.response_time_ms = None
    coordinator.last_successful_read = None
    return coordinator


class WriteRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_single_write_preserves_fc06(self):
        coordinator = make_coordinator()
        await coordinator.async_write_register(4446, 15656)
        coordinator.unit.write_register.assert_awaited_once_with(4446, 15656)
        coordinator.unit.write_registers.assert_not_awaited()

    async def test_timeout_after_applied_write_is_verified(self):
        coordinator = make_coordinator()
        coordinator.unit.write_register.side_effect = TimeoutError('Response timeout')
        coordinator._read_holding.return_value = [15656]
        await coordinator.async_write_register(4446, 15656)
        coordinator.unit.disconnect.assert_awaited_once()
        coordinator.unit.write_registers.assert_not_awaited()

    async def test_timeout_switches_to_fc16_and_reuses_it(self):
        coordinator = make_coordinator()
        coordinator.unit.write_register.side_effect = TimeoutError('Response timeout')
        await coordinator.async_write_register(4446, 15656)
        await coordinator.async_write_register(259, 50)
        self.assertEqual(coordinator.unit.write_register.await_count, 1)
        self.assertEqual(coordinator.unit.write_registers.await_args_list[0].args, (4446, [15656]))
        self.assertEqual(coordinator.unit.write_registers.await_args_list[1].args, (259, [50]))

    async def test_failed_readback_still_attempts_fc16(self):
        coordinator = make_coordinator()
        coordinator.unit.write_register.side_effect = TimeoutError('Response timeout')
        coordinator._read_holding.side_effect = TimeoutError('Response timeout')
        await coordinator.async_write_register(4446, 15656)
        coordinator.unit.write_registers.assert_awaited_once_with(4446, [15656])

    async def test_rejected_write_is_reported(self):
        coordinator = make_coordinator()
        coordinator.unit.write_register.side_effect = ValueError('illegal value')
        with self.assertRaisesRegex(ValueError, 'illegal value'):
            await coordinator.async_write_register(4446, 15656)
        coordinator.unit.write_registers.assert_not_awaited()

    async def test_multi_write_lost_acknowledgement_is_verified(self):
        coordinator = make_coordinator()
        coordinator.unit.write_registers.side_effect = TimeoutError('Response timeout')
        coordinator._read_holding.return_value = [12, 30]
        await coordinator.async_write_registers(4449, [12, 30])
        coordinator.unit.write_registers.assert_awaited_once()

    async def test_failed_multi_write_retries_then_raises(self):
        coordinator = make_coordinator()
        coordinator.unit.write_registers.side_effect = TimeoutError('Response timeout')
        with self.assertRaises(TimeoutError):
            await coordinator.async_write_registers(4449, [12, 30])
        self.assertEqual(coordinator.unit.write_registers.await_count, 2)

    async def test_control_cache_tracks_success_and_rollback(self):
        coordinator = make_coordinator()
        coordinator.async_set_updated_data({'r4446': 15656})
        self.assertEqual(coordinator._last_data, coordinator.data)
        coordinator.async_set_updated_data({'r4446': 10280})
        self.assertEqual(coordinator._last_data, {'r4446': 10280})


class FakeEntity:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.states = []

    def async_write_ha_state(self):
        self.states.append(self.current_option if hasattr(type(self), 'current_option') else self.native_value)


def control_types():
    control_namespace = load_definitions('control.py', {'optimistic_control', 'control_state_attributes'}, {'wraps': wraps, 'asyncio': asyncio})
    decorator = control_namespace['optimistic_control']
    namespace = {
        'SolarInverterCoordinator': object,
        'CoordinatorEntity': FakeEntity, 'NumberEntity': type('NumberEntity', (), {}),
        'SelectEntity': type('SelectEntity', (), {}), 'TimeEntity': type('TimeEntity', (), {}),
        'NumberMode': SimpleNamespace(AUTO='auto', SLIDER='slider'),
        'NumberDeviceClass': SimpleNamespace(POWER='power'), 'UnitOfPower': SimpleNamespace(WATT='W'),
        'EntityCategory': SimpleNamespace(CONFIG='config'),
        'DOMAIN': 'solar_inverter_modbus_tcp', 'OPTIONS': ['Self Use', 'Backup'],
        'EMS_MODES': {0: 'Self Use', 1: 'Backup'}, 'NAME_TO_VALUE': {'Self Use': 0, 'Backup': 1},
        'inverter_device_info': lambda coordinator: {}, 'ev_charger_device_info': lambda coordinator: {},
        '_LOGGER': logging.getLogger(__name__), '_INTER_REQUEST_DELAY': 0,
        'asyncio': asyncio, 'time': __import__('time'), 'optimistic_control': decorator,
        'control_state_attributes': control_namespace['control_state_attributes'],
    }
    load_definitions('number.py', {'PeakShavingNumber', 'ExportPowerLimitNumber', 'BatterySettingNumber', 'EmsSettingNumber', 'EvChargerPowerNumber'}, namespace)
    load_definitions('select.py', {'SolarInverterEmsSelect', 'EvChargerSettingSelect'}, namespace)
    # time.py uses datetime.time rather than the time module.
    time_namespace = load_definitions('time.py', {'TouPeriodTime'}, dict(namespace, time=datetime_time))
    namespace['TouPeriodTime'] = time_namespace['TouPeriodTime']
    return namespace


class ImmediateFeedbackTests(unittest.IsolatedAsyncioTestCase):
    def make_controls(self):
        coordinator = make_coordinator()
        coordinator.modbus_lock = asyncio.Lock()
        coordinator.debug_logging = False
        coordinator.entry_id = 'entry'
        coordinator.export_limit_watts = 1000
        coordinator.inverter_rated_power_watts = 10000
        coordinator.async_set_updated_data({
            'r4446': 10280, 'peak_meter_baseline_soc': 40, 'peak_meter_reserved_soc': 40,
            'r259': 0, 'r306': 400, 'r4300': 0, 'ems_mode': 0,
            'r4301': 40, 'r4700': 20, 'r4702': 1, 'r4449': 8, 'r4450': 0,
        })

        async def read(address, count):
            return [coordinator.data.get(f'r{register}', 0) for register in range(address, address + count)]

        coordinator.unit.read_holding_registers = AsyncMock(side_effect=read)
        classes = control_types()
        controls = [
            (classes['PeakShavingNumber'](coordinator, 'peak_meter_baseline_soc', 'Baseline', 10, 100, 1, True), 61),
            (classes['PeakShavingNumber'](coordinator, 'peak_meter_reserved_soc', 'Reserved', 10, 100, 1, False), 50),
            (classes['ExportPowerLimitNumber'](coordinator), 500),
            (classes['BatterySettingNumber'](coordinator, 'battery', 'Battery', 306, 0, 100, 0.1), 50),
            (classes['EmsSettingNumber'](coordinator, 'ems', 'EMS', 4301, 10, 100, 1, '%', 'slider'), 50),
            (classes['EvChargerPowerNumber'](coordinator, 'power', 'Power', 4700, 11), 5),
            (classes['SolarInverterEmsSelect'](coordinator), 'Backup'),
            (classes['EvChargerSettingSelect'](coordinator, 'mode', 'Mode', 4702, {'Plug': 1, 'RFID': 2}), 'RFID'),
            (classes['TouPeriodTime'](coordinator, 'start', 'Start', 4449), datetime_time(12, 30)),
        ]
        return coordinator, controls

    def setter(self, entity):
        if hasattr(entity, 'async_select_option'):
            return entity.async_select_option
        if hasattr(entity, 'async_set_native_value'):
            return entity.async_set_native_value
        return entity.async_set_value

    async def test_all_controls_show_value_while_polling_holds_lock(self):
        coordinator, controls = self.make_controls()
        for entity, value in controls:
            with self.subTest(entity=type(entity).__name__):
                await coordinator.modbus_lock.acquire()
                self.assertEqual(entity.extra_state_attributes['write_status'], 'idle')
                task = asyncio.create_task(self.setter(entity)(value))
                await asyncio.sleep(0)
                self.assertEqual(entity.states[-1], value)
                self.assertEqual(entity.extra_state_attributes['write_status'], 'pending')
                self.assertFalse(task.done())
                coordinator.modbus_lock.release()
                await task
                self.assertEqual(entity.states[-1], value)
                self.assertEqual(entity.extra_state_attributes['write_status'], 'confirmed')
                self.assertIsNone(entity.extra_state_attributes['write_error'])
                self.assertEqual(coordinator._last_data, coordinator.data)

    async def test_all_controls_restore_state_on_failure(self):
        coordinator, controls = self.make_controls()
        coordinator.async_write_register = AsyncMock(side_effect=RuntimeError('write rejected'))
        coordinator.async_write_registers = AsyncMock(side_effect=RuntimeError('write rejected'))
        for entity, value in controls:
            with self.subTest(entity=type(entity).__name__):
                previous = dict(coordinator.data)
                old_value = entity.current_option if hasattr(type(entity), 'current_option') else entity.native_value
                with self.assertRaisesRegex(RuntimeError, 'write rejected'):
                    await self.setter(entity)(value)
                self.assertEqual(entity.states[0], value)
                self.assertEqual(entity.states[-1], old_value)
                self.assertEqual(coordinator.data, previous)
                self.assertEqual(entity.extra_state_attributes['write_status'], 'error')
                self.assertEqual(entity.extra_state_attributes['write_error'], 'write rejected')

    async def test_cancelled_queued_control_clears_preview(self):
        coordinator, controls = self.make_controls()
        entity, value = controls[0]
        await coordinator.modbus_lock.acquire()
        task = asyncio.create_task(self.setter(entity)(value))
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        coordinator.modbus_lock.release()
        self.assertEqual(entity.native_value, 40)
        self.assertEqual(entity.extra_state_attributes['write_status'], 'cancelled')

    async def test_new_request_clears_previous_error(self):
        coordinator, controls = self.make_controls()
        entity, value = controls[0]
        coordinator.async_write_register = AsyncMock(side_effect=RuntimeError('write rejected'))
        with self.assertRaises(RuntimeError):
            await self.setter(entity)(value)
        coordinator.async_write_register = AsyncMock()
        await coordinator.modbus_lock.acquire()
        task = asyncio.create_task(self.setter(entity)(value))
        await asyncio.sleep(0)
        self.assertEqual(entity.extra_state_attributes['write_status'], 'pending')
        self.assertIsNone(entity.extra_state_attributes['write_error'])
        coordinator.modbus_lock.release()
        await task
        self.assertEqual(entity.extra_state_attributes['write_status'], 'confirmed')

    async def test_newest_queued_value_survives_older_completion(self):
        coordinator, controls = self.make_controls()
        entity, _ = controls[0]
        await coordinator.modbus_lock.acquire()
        first = asyncio.create_task(self.setter(entity)(50))
        second = asyncio.create_task(self.setter(entity)(60))
        await asyncio.sleep(0)
        self.assertEqual(entity.native_value, 60)
        coordinator.modbus_lock.release()
        await first
        self.assertEqual(entity.native_value, 60)
        self.assertEqual(entity.extra_state_attributes['write_status'], 'pending')
        await second
        self.assertEqual(entity.native_value, 60)
        self.assertEqual(entity.extra_state_attributes['write_status'], 'confirmed')


if __name__ == '__main__':
    unittest.main()
