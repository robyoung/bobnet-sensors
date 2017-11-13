from unittest import mock

import pytest

from bobnet_sensors import iotcore


@pytest.fixture(scope='session')
def private_key():
    with open('tests/fixtures/private-key.pem') as f:
        return f.read()


@pytest.fixture
def valid_config():
    return {
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
def iotcore_connection(mock_mqtt, private_key):
    return iotcore.Connection(
        'europe-west1',
        'test-project',
        'test-registry',
        'test01',
        private_key,
        './tests/fixtures/roots.pem',
    )
