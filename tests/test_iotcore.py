from unittest import mock
from collections import namedtuple

import pytest
import jwt

from bobnet_sensors import iotcore


@pytest.mark.parametrize('rc,error', [
    (0, '0: No error.'),
    (1, '1: Out of memory.'),
    (234, '234: Unknown error.'),
])
def test_error_str(rc, error):
    assert iotcore.error_str(rc) == error


def test_load_private_key_returns_private_key():
    config = {'private_key': 'super secret'}

    assert iotcore.load_private_key(config) == 'super secret'


@mock.patch('bobnet_sensors.iotcore.open', create=True)
def test_load_private_key_loads_key_from_file(mock_open):
    # arrange
    mock_open.return_value = mock.MagicMock()
    mock_file = mock_open.return_value.__enter__.return_value
    mock_file.read.return_value = 'also secret'
    config = {'private_key_path': '/path/to/private.pem'}

    # act
    private_key = iotcore.load_private_key(config)

    # assert
    assert private_key == 'also secret'
    mock_open.assert_called_with('/path/to/private.pem')


@mock.patch('os.path.exists')
@mock.patch('urllib.request.urlopen')
@mock.patch('bobnet_sensors.iotcore.open')
def test_load_ca_certs_downloads_root_cert_if_not_there(
    mock_open, mock_urlopen, mock_exists
):
    # arrange
    mock_open.return_value = mock.MagicMock()
    mock_file = mock_open.return_value.__enter__.return_value

    mock_urlopen.return_value = mock.MagicMock()
    mock_url = mock_urlopen.return_value.__enter__.return_value
    mock_url.read.return_value = b'google roots'

    mock_exists.return_value = False

    # act
    iotcore.load_ca_certs('/path/to/roots.pem')

    # assert
    mock_exists.assert_called_with('/path/to/roots.pem')
    mock_file.write.assert_called_with('google roots')


@mock.patch('os.path.exists')
@mock.patch('urllib.request.urlopen')
def test_load_ca_certs_does_nothing_if_cert_is_there(
    mock_urlopen, mock_exists
):
    # arrange
    mock_exists.return_value = True

    # act
    iotcore.load_ca_certs('/path/to/roots.pem')

    # assert
    assert not mock_urlopen.called


def test_create_jwt(private_key):
    # arrange
    project_id = 'bobnet-project'

    # act
    token = iotcore.create_jwt(project_id, private_key)

    # assert
    payload = jwt.decode(token, private_key,
                         algorithms=['RS256'], verify=False)
    assert payload == {
        'aud': 'bobnet-project',
        'iat': mock.ANY,
        'exp': mock.ANY,
    }


def test_create_connection_from_config(mock_mqtt, valid_config, private_key):
    conn = iotcore.Connection.from_config(valid_config)

    assert conn.region == 'europe-west1'
    assert conn.private_key == private_key


def test_create_connection_from_config_fails_on_missing_keys(
    mock_mqtt, valid_config
):
    del valid_config['iotcore']['region']
    with pytest.raises(KeyError):
        iotcore.Connection.from_config(valid_config)


def test_connection_connect(mock_mqtt_client, iotcore_connection):
    conn = iotcore_connection
    mock_connect_event = mock.Mock()
    mock_connect_event.wait.return_value = True
    conn.connect_event = mock_connect_event

    conn.connect()

    assert mock_mqtt_client.connect.called
    assert mock_mqtt_client.loop_start.called
    assert mock_connect_event.wait.called
    mock_mqtt_client.subscribe.assert_called_with('/devices/test01/config',
                                                  qos=1)


def test_on_connect_event(mock_mqtt_client, iotcore_connection):
    conn = iotcore_connection
    conn.connect_event = mock.Mock()

    conn.on_connect(None, None, None, None)

    assert mock_mqtt_client.on_connect == conn.on_connect
    assert conn.connected
    assert conn.connect_event.set.called


def test_on_disconnect_event(mock_mqtt_client, iotcore_connection):
    conn = iotcore_connection
    conn.connect_event = mock.Mock()

    conn.on_disconnect(None, None, None)

    assert mock_mqtt_client.on_disconnect == conn.on_disconnect
    assert not conn.connected
    assert conn.connect_event.clear.called


def test_on_subscribe_fails_on_qos_failure(iotcore_connection):
    conn = iotcore_connection

    with pytest.raises(RuntimeError):
        conn.on_subscribe(None, None, None, (128,))


Message = namedtuple('Message', 'payload')


def test_on_message_sets_message(iotcore_connection):
    conn = iotcore_connection
    message = Message('{"foo": "bar"}'.encode('utf8'))

    conn.on_message(None, None, message)

    assert conn.message == {'foo': 'bar'}
    assert conn.has_message_event.is_set()
    assert conn.new_message_event.is_set()


def test_on_message_sets_no_message_if_no_payload(iotcore_connection):
    conn = iotcore_connection
    message = Message(''.encode('utf8'))

    conn.on_message(None, None, message)

    assert not conn.has_message_event.is_set()
    assert not conn.new_message_event.is_set()


def test_publish_message(mock_mqtt_client, iotcore_connection):
    conn = iotcore_connection

    conn.publish({'foo': 'bar'})

    mock_mqtt_client.publish.assert_called_once_with(
        '/devices/test01/events', '{"foo": "bar"}',
        qos=1)


@mock.patch('bobnet_sensors.iotcore.Connection')
def test_load_iotcore(mock_Connection):
    client = iotcore.load_iotcore({})
    client.send('message')

    assert mock_Connection.from_config.return_value.connect.called
