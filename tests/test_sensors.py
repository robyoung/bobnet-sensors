from unittest import mock
from datetime import datetime
import asyncio

import pytest

from conftest import roughly, sleep_short
from bobnet_sensors.sensors import (
    Sensors, Sensor, parse_time, BaseDevice,
    get_device_class
)
from bobnet_sensors.sensors.counter import Device as CounterDevice
# from bobnet_sensors.sensors.mcp3008 import Device as MCP3008Device
from bobnet_sensors.models import (
    ConfigMessage, CommandMessage, LogMessage
)


@pytest.mark.parametrize('t,result', [
    ('0.1s', 0.1),
    ('10s', 10),
    ('10m', 10 * 60),
    ('10h', 10 * 60 * 60),
])
def test_parse_time(t, result):
    assert parse_time(t) == result


def test_get_device_class():
    assert get_device_class('counter') == CounterDevice


def test_parse_time_failure_raises_value_error():
    with pytest.raises(ValueError):
        parse_time('bad time')


def test_apply_control_messages_config(looper, mock_sensor_set):
    sensors = Sensors(mock_sensor_set)
    message = ConfigMessage('sensor1', {'foo': 'bar'})

    results = list(sensors.apply_control_message(looper, message))

    assert results == []
    assert_update_config_called_once(
        mock_sensor_set, 'sensor1', {'foo': 'bar'}
    )


def test_apply_control_messages_command(looper, mock_sensor_set):
    sensors = Sensors(mock_sensor_set)
    message = CommandMessage('sensor1', 1, 'new', None)

    result = list(sensors.apply_control_message(looper, message))

    assert result == [CommandMessage('sensor1', 1, 'ack',
                                     roughly(datetime.utcnow()))]
    assert_no_update_config_called(mock_sensor_set)


def test_apply_control_messages_invalid(looper, mock_sensor_set):
    sensors = Sensors(mock_sensor_set)
    message = 'invalid'

    result = list(sensors.apply_control_message(looper, message))

    assert result == [LogMessage.error('Invalid control message invalid')]
    assert_no_update_config_called(mock_sensor_set)


def assert_update_config_called_once(mock_sensor_set, device_name, config):
    for name, device in mock_sensor_set.items():
        if name == device_name:
            device.update_config.assert_called_once_with(config)
        else:
            assert not device.update_config.called


def assert_no_update_config_called(mock_sensor_set):
    for device in mock_sensor_set.values():
        assert not device.update_config.called


def assert_run_command_called_once(mock_sensor_set, device_name, looper):
    for name, device in mock_sensor_set.items():
        if name == device_name:
            device.run_command.assert_called_once_with(looper)
        else:
            assert not device.run_command.called


def assert_no_run_command_called(mock_sensor_set):
    for device in mock_sensor_set.values():
        if hasattr(device, 'run_command'):
            assert not device.run_command.called


def test_apply_config_message_ok(looper, mock_sensor_set):
    sensors = Sensors(mock_sensor_set)
    message = ConfigMessage('sensor1', {'foo': 'bar'})

    results = list(sensors.apply_config_message(looper, message))

    assert results == []
    assert_update_config_called_once(
        mock_sensor_set, 'sensor1', {'foo': 'bar'}
    )


def test_apply_config_message_error(looper, mock_sensor_set):
    sensors = Sensors(mock_sensor_set)
    message = ConfigMessage('sensor1', {'foo': 'bar'})
    mock_sensor_set['sensor1'].update_config.return_value = (False, 'fail')

    result = list(sensors.apply_config_message(looper, message))

    assert result == [LogMessage.error('Config error on sensor1: fail')]
    assert_update_config_called_once(
        mock_sensor_set, 'sensor1', {'foo': 'bar'}
    )


def test_apply_config_message_no_device(looper, mock_sensor_set):
    sensors = Sensors(mock_sensor_set)
    message = ConfigMessage('invalid', {'foo': 'bar'})

    result = list(sensors.apply_config_message(looper, message))

    assert result == [LogMessage.error('Unknown device in config invalid')]
    assert_no_update_config_called(mock_sensor_set)


def test_apply_command_message_ok(looper, mock_sensor_set):
    sensors = Sensors(mock_sensor_set)
    message = CommandMessage('sensor1', 1, 'new', None)

    results = list(sensors.apply_command_message(looper, message))
    # allow the future to run
    looper.loop.run_until_complete(sleep_short())

    assert results == [CommandMessage('sensor1', 1, 'ack',
                                      roughly(datetime.utcnow()))]
    assert_run_command_called_once(mock_sensor_set, 'sensor1', looper)


def test_apply_command_message_no_run_command(looper, mock_sensor_set):
    del mock_sensor_set['sensor1'].run_command
    sensors = Sensors(mock_sensor_set)
    message = CommandMessage('sensor1', 1, 'new', None)

    results = list(sensors.apply_command_message(looper, message))

    assert results == [LogMessage.error('Device sensor1 has no run_command')]
    assert_no_run_command_called(mock_sensor_set)


def test_apply_command_message_should_not_run(looper, mock_sensor_set):
    sensors = Sensors(mock_sensor_set)
    message = CommandMessage('sensor1', 1, 'ack', datetime.utcnow())

    results = list(sensors.apply_command_message(looper, message))

    assert results == []
    assert_no_run_command_called(mock_sensor_set)


def test_apply_command_message_no_device(looper, mock_sensor_set):
    sensors = Sensors(mock_sensor_set)
    message = CommandMessage('invalid', 1, 'new', None)

    result = list(sensors.apply_command_message(looper, message))

    assert result == [LogMessage.error('Unknown device in command invalid')]


def test_run_update_config(looper, mock_sensor_set):
    sensors = Sensors(mock_sensor_set)
    answers = []

    async def control():
        await looper.config_queue.put(
            ConfigMessage('sensor1', {'foo': 'bar'})
        )
        await looper.config_queue.put(
            CommandMessage('sensor1', 1, 'new', None)
        )
        answers.append(await looper.send_queue.get())
        looper.stop()

    looper.loop.run_until_complete(
        asyncio.gather(
            control(),
            sensors.run_update_config(looper),
            loop=looper.loop
        )
    )

    assert looper.send_queue.queue.async_q.qsize() == 0
    assert answers == [CommandMessage('sensor1', 1, 'ack',
                                      roughly(datetime.utcnow()))]
    assert_update_config_called_once(
        mock_sensor_set, 'sensor1', {'foo': 'bar'}
    )
    assert_run_command_called_once(
        mock_sensor_set, 'sensor1', looper
    )


def test_run_update_config_with_error(looper, mock_sensor_set):
    sensors = Sensors(mock_sensor_set)
    answers = []

    async def control():
        await looper.config_queue.put(
            ConfigMessage('invalid', {'foo': 'bar'})
        )
        await asyncio.sleep(0.001)
        answers.append(await looper.send_queue.get())
        looper.stop()

    looper.loop.run_until_complete(
        asyncio.gather(
            control(),
            sensors.run_update_config(looper),
            loop=looper.loop
        )
    )

    assert looper.send_queue.queue.async_q.qsize() == 0
    assert answers == [LogMessage.error('Unknown device in config invalid')]
    assert_no_update_config_called(mock_sensor_set)


def test_create_sensors_from_config(mock_mcp3008, valid_config):
    sensors = Sensors.from_config(valid_config)

    sensors = list(sensors)
    assert len(sensors) == 1
    assert sensors[0].name == 'mcp3008'
    assert sensors[0].every == 10
    assert isinstance(sensors[0].device, BaseDevice)


def test_update_config_on_single_sensor():
    mock_device = mock.Mock()
    config = {'every': '10s', 'other': 'value'}
    sensor = Sensor('sensor1', '30s', mock_device)

    ok, error = sensor.update_config(config)

    assert ok
    assert sensor.every == 10
    mock_device.update_config.assert_called_with(config)


def test_update_config_without_every():
    mock_device = mock.Mock()
    config = {'other': 'value'}
    sensor = Sensor('sensor1', '10s', mock_device)

    ok, error = sensor.update_config(config)

    assert ok
    assert sensor.every == 10
    mock_device.update_config.assert_called_with(config)


def test_update_config_failure():
    mock_device = mock.Mock()
    config = {'other': 'value'}
    sensor = Sensor('sensor1', '10s', mock_device)
    mock_device.update_config.side_effect = ValueError('bad thing')

    ok, error = sensor.update_config(config)

    assert not ok
    assert error == 'bad thing'


def test_sensor_run(looper):
    async def do_task(looper):
        value = await looper.send_queue.get()
        looper.stop()
        return value

    sensor = Sensor('name', '10s', mock.Mock())

    results = looper.loop.run_until_complete(
        asyncio.gather(
            sensor.run(looper),
            do_task(looper),
            loop=looper.loop
        )
    )

    assert results == [
        None, {'sensor': 'name', 'value': mock.ANY}
    ]
