import asyncio
from unittest import mock

import pytest

import bobnet_sensors
bobnet_sensors.TESTING = True

from bobnet_sensors import iotcore  # noqa
from bobnet_sensors.sensors import Sensors, Sensor  # noqa


async def return_immediately():
    pass


@pytest.fixture(scope='session')
def private_key():
    with open('tests/fixtures/private-key.pem') as f:
        return f.read()


@pytest.fixture
def loop():
    return asyncio.new_event_loop()


@pytest.fixture
def stop(loop):
    return asyncio.Event(loop=loop)


@pytest.fixture
def valid_config():
    return {
        'sensors': {
            'mcp3008': {
                'device': 'mcp3008',
                'every': '10s',
                'channels': [
                    {'channel': 0, 'label': 'temp'},
                    {'channel': 1, 'label': 'light'}
                ]
            },
        },
        'iotcore': {
            'region': 'europe-west1',
            'project_id': 'test-project',
            'registry_id': 'test-registry',
            'device_id': 'test01',
            'private_key_path': './tests/fixtures/private-key.pem',
            'ca_certs_path': './tests/fixtures/roots.pem',
        }
    }


@pytest.fixture
def mock_mqtt():
    with mock.patch('bobnet_sensors.iotcore.mqtt') as mock_mqtt:
        yield mock_mqtt


@pytest.fixture
def mock_mqtt_client(mock_mqtt):
    yield mock_mqtt.Client.return_value


@pytest.fixture
def mock_on_message():
    yield mock.Mock()


@pytest.fixture
def iotcore_connection(mock_on_message, private_key):
    conn = iotcore.Connection(
        'europe-west1',
        'test-project',
        'test-registry',
        'test01',
        private_key,
        './tests/fixtures/roots.pem',
        mock_on_message,
    )
    # Client is only created on connect so mock it out for tests
    conn._client = mock.Mock()
    return conn


@pytest.fixture
def mock_iotcore_conn(loop):
    mock_connection = mock.Mock()
    mock_connection.has_message_event = asyncio.Event(loop=loop)
    mock_connection.new_message_event = asyncio.Event(loop=loop)
    mock_connection.connect = return_immediately
    mock_connection._wait_for_connection = return_immediately

    return mock_connection


@pytest.fixture
def iotcore_client(mock_iotcore_conn):
    return iotcore.IOTCoreClient(mock_iotcore_conn)


@pytest.fixture
def mock_sensor_set():
    mock_sensors = {}
    for i in range(1, 3):
        mock_sensor = mock.Mock()
        mock_sensor.update_config.return_value = (True, '')
        mock_sensors[f'sensor{i}'] = mock_sensor
    return mock_sensors


@pytest.fixture
def sensor_set():
    result = {}
    for i in range(1, 3):
        mock_device = mock.Mock()
        mock_device.value = f'device{i} value'
        sensor = Sensor(f'sensor{i}', '10s', mock_device)
        result[sensor.name] = sensor

    return result


@pytest.fixture(autouse=True)
def mock_mcp3008():
    with mock.patch('bobnet_sensors.sensors.mcp3008.MCP3008') as m:
        yield m


@pytest.fixture(autouse=True)
def mock_RPi():
    with mock.patch('bobnet_sensors.sensors.mcp3008.RPi') as m:
        yield m


@pytest.fixture
def sensors(sensor_set):
    return Sensors(sensor_set)
