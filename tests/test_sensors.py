from unittest import mock
import asyncio

import pytest

from bobnet_sensors.sensors import (
    Sensors, Sensor, parse_time, BaseDevice, MCP3008Device
)


@pytest.fixture
def mock_sensors():
    mock_sensors = {}
    for i in range(1, 3):
        mock_sensor = mock.Mock()
        mock_sensor.update_config.return_value = (True, '')
        mock_sensors[f'sensor{i}'] = mock_sensor
    return mock_sensors


@pytest.fixture
def mock_mcp3008():
    with mock.patch('bobnet_sensors.sensors.MCP3008') as m:
        yield m


@pytest.fixture
def sensors_config():
    return {
        'sensors': {
            'temp': {
                'device': 'MCP3008',
                'every': '10s',
                'channel': 0,
            },
            'light': {
                'device': 'MCP3008',
                'every': '30s',
                'channel': 1,
            }
        }
    }


@pytest.mark.parametrize('t,result', [
    ('10s', 10),
    ('10m', 10 * 60),
    ('10h', 10 * 60 * 60),
])
def test_parse_time(t, result):
    assert parse_time(t) == result


def test_parse_time_failure_raises_value_error():
    with pytest.raises(ValueError):
        parse_time('bad time')


def test_update_config_success_on_all_sensors(mock_sensors):
    sensors = Sensors(mock_sensors)

    ok, errors = sensors.update_config({
        'sensors': {
            'sensor1': 'config1',
            'sensor2': 'config2'
        }
    })

    assert ok
    assert not errors


def test_update_config_for_unknown_sensor_gets_ignored(mock_sensors):
    sensors = Sensors(mock_sensors)

    ok, errors = sensors.update_config({
        'sensors': {
            'sensor3': 'config'
        }
    })

    assert ok
    assert not errors


def test_update_config_any_error_causes_error(mock_sensors):
    mock_sensors['sensor1'].update_config.return_value = (False, 'bad')
    sensors = Sensors(mock_sensors)

    ok, errors = sensors.update_config({
        'sensors': {
            'sensor1': 'config1',
            'sensor2': 'config2'
        }
    })

    assert not ok
    assert errors == ['bad']


def test_create_sensors_from_config(mock_mcp3008, sensors_config):
    sensors = Sensors.from_config(sensors_config)

    sensors = list(sensors)
    assert len(sensors) == 2
    assert sensors[0].name == 'temp'
    assert sensors[0].every == 10
    assert isinstance(sensors[1].device, BaseDevice)


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


def test_read_value_from_mcp3008(mock_mcp3008):
    mock_mcp3008.return_value.value = 'value'
    device = MCP3008Device(1)

    assert device.value == 'value'
    mock_mcp3008.assert_called_with(
        channel=1, clock_pin=18,
        mosi_pin=24, miso_pin=23, select_pin=25)


def test_sensor_run():
    loop = asyncio.new_event_loop()
    stop = asyncio.Event(loop=loop)
    values = asyncio.Queue(loop=loop)

    async def test_task(stop, values):
        value = await values.get()
        stop.set()
        return value

    sensor = Sensor('name', '10s', mock.Mock())

    results = loop.run_until_complete(
        asyncio.gather(
            sensor.run(stop, values),
            test_task(stop, values),
            loop=loop
        )
    )

    assert results == [
        None, {'sensor': 'name', 'value': mock.ANY}
    ]
