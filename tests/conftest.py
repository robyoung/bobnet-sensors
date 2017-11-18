import asyncio
from unittest import mock

import pytest

from bobnet_sensors import iotcore
from bobnet_sensors.sensors import Sensors


@pytest.fixture(scope='session')
def private_key():
    with open('tests/fixtures/private-key.pem') as f:
        return f.read()


@pytest.fixture
def loop():
    return asyncio.new_event_loop()


@pytest.fixture
def valid_config():
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
def iotcore_connection(loop, mock_mqtt, private_key):
    return iotcore.Connection(
        loop,
        'europe-west1',
        'test-project',
        'test-registry',
        'test01',
        private_key,
        './tests/fixtures/roots.pem',
    )

@pytest.fixture
def mock_iotcore_conn(loop):
    mock_connection = mock.Mock()
    mock_connection.has_message_event = asyncio.Event(loop=loop)
    mock_connection.new_message_event = asyncio.Event(loop=loop)

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
def mock_mcp3008():
    with mock.patch('bobnet_sensors.sensors.MCP3008') as m:
        yield m


@pytest.fixture
def sensors(mock_sensor_set):
    return Sensors(mock_sensor_set)
