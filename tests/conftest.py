import asyncio
from unittest import mock
from datetime import datetime, timedelta

import pytest

import bobnet_sensors
bobnet_sensors.TESTING = True

from bobnet_sensors import iotcore  # noqa: E402
from bobnet_sensors.sensors import Sensors, Sensor  # noqa: E402
from bobnet_sensors.async_helper import Looper  # noqa: E402


async def return_immediately():
    pass


async def sleep_short():
    await asyncio.sleep(0.001)


class roughly:
    def __init__(self, target, slop=None):
        self.target = target
        self.slop = slop or self._default_slop(target)

    @staticmethod
    def _default_slop(target):
        if isinstance(target, datetime):
            return timedelta(seconds=10)
        raise TypeError('target not supported')

    def __eq__(self, other):
        return self.target - self.slop < other < self.target + self.slop


@pytest.fixture(scope='session')
def private_key():
    with open('tests/fixtures/private-key.pem') as f:
        return f.read()


@pytest.fixture
def loop():
    the_loop = asyncio.new_event_loop()
    yield the_loop
    the_loop.run_until_complete(the_loop.shutdown_asyncgens())
    the_loop.close()


@pytest.fixture
def looper(loop):
    return Looper(loop)


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
def iotcore_connection(looper, private_key):
    conn = iotcore.Connection(
        looper,
        'europe-west1',
        'test-project',
        'test-registry',
        'test01',
        private_key,
        './tests/fixtures/roots.pem',
    )
    # Client is only created on connect so mock it out for tests
    conn._client = mock.Mock()
    return conn


@pytest.fixture
def mock_iotcore_conn(loop):
    mock_connection = mock.Mock()

    return mock_connection


@pytest.fixture
def iotcore_client(mock_iotcore_conn):
    return iotcore.IOTCoreClient(mock_iotcore_conn)


class AsyncMock(mock.MagicMock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


@pytest.fixture
def mock_sensor_set():
    mock_sensors = {}
    for i in range(1, 3):
        mock_sensor = mock.Mock()
        mock_sensor.update_config.return_value = (True, '')
        mock_sensor.run_command = AsyncMock()
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
