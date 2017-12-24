import asyncio
from unittest import mock
from collections import namedtuple

import pytest
import jwt

from bobnet_sensors import iotcore
from conftest import return_immediately


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


def test_create_connection_from_config(
    loop, mock_mqtt, valid_config, private_key
):
    # act
    conn = iotcore.Connection.from_config(valid_config)

    # assert
    assert conn.region == 'europe-west1'
    assert conn.private_key == private_key


def test_create_connection_from_config_fails_on_missing_keys(
    loop, mock_mqtt, valid_config
):
    # arrange
    del valid_config['iotcore']['region']

    # act and assert
    with pytest.raises(KeyError):
        iotcore.Connection.from_config(valid_config)


def test_connection_connect(mock_mqtt_client, iotcore_connection):
    # arrange
    conn = iotcore_connection

    # act
    conn.connect()

    # assert
    assert mock_mqtt_client.connect.called
    assert mock_mqtt_client.loop_start.called
    assert not mock_mqtt_client.subscribe.called


def test_on_connect_event(iotcore_connection):
    # arrange
    conn = iotcore_connection

    # act
    conn.on_connect(None, None, None, None)

    # assert
    conn._client.subscribe.assert_called_with('/devices/test01/config',
                                              qos=1)
    assert conn.connected
    assert conn.connect_event.is_set()


def test_on_disconnect_event(mock_mqtt_client, iotcore_connection):
    # arrange
    conn = iotcore_connection
    conn.connect_event.set()
    mock_client = conn._client

    # act
    conn.on_disconnect(None, None, None)

    # assert
    assert not conn.connected
    assert not conn.connect_event.is_set()
    assert mock_client.loop_stop.called


def test_on_subscribe_fails_on_qos_failure(iotcore_connection):
    # arrange
    conn = iotcore_connection

    # act and assert
    with pytest.raises(RuntimeError):
        conn.on_subscribe(None, None, None, (128,))


Message = namedtuple('Message', 'payload')


def test_on_message_sends_message(mock_on_message, iotcore_connection):
    # arrange
    conn = iotcore_connection
    message = Message('{"foo": "bar"}'.encode('utf8'))

    # act
    conn.on_message(None, None, message)

    # assert
    called_message = mock_on_message.call_args[0][0]
    assert called_message == {'foo': 'bar'}


def test_on_message_sends_no_message_if_no_payload(
    mock_on_message, iotcore_connection
):
    # arrange
    conn = iotcore_connection
    message = Message(''.encode('utf8'))

    # act
    conn.on_message(None, None, message)

    # assert
    assert not mock_on_message.called


def test_publish_message(iotcore_connection):
    # arrange
    conn = iotcore_connection
    conn.connect_event.set()

    # act
    conn.publish({'foo': 'bar'})

    # assert
    conn._client.publish.assert_called_once_with(
        '/devices/test01/events', '{"foo": "bar"}',
        qos=1)


@mock.patch('bobnet_sensors.iotcore.Connection')
def test_load_iotcore(mock_Connection, loop):
    # arrange
    mock_connect = mock.Mock()

    mock_Connection.from_config.return_value.connect = mock_connect

    # act
    client = iotcore.load_iotcore(loop, {})

    # assert
    assert client._client == mock_Connection.from_config.return_value


def test_run_send_stop_no_value(loop):
    stop = asyncio.Event(loop=loop)
    values = asyncio.Queue(loop=loop)

    async def test_task(stop, values):
        stop.set()

    mock_client = mock.Mock()

    client = iotcore.IOTCoreClient(mock_client)

    loop.run_until_complete(
        asyncio.gather(
            client.run_send(loop, stop, values),
            test_task(stop, values),
            loop=loop
        )
    )

    assert not mock_client.publish.called


def test_run_send_value_then_stop(loop):
    stop = asyncio.Event(loop=loop)
    values = asyncio.Queue(loop=loop)

    async def test_task(stop, values):
        await values.put('test value')
        await asyncio.sleep(0.0001)
        stop.set()

    mock_client = mock.Mock()
    mock_client._wait_for_connection = return_immediately

    client = iotcore.IOTCoreClient(mock_client)

    loop.run_until_complete(
        asyncio.gather(
            client.run_send(loop, stop, values),
            test_task(stop, values),
            loop=loop
        )
    )

    mock_client.publish.assert_called_with('test value')


def test_setup_config_handler():
    # arrange
    mock_target = mock.Mock()
    mock_target.update_config.return_value = (True, None)
    mock_client = mock.Mock()
    client = iotcore.IOTCoreClient(mock_client)

    # act
    client.setup_config_handler(mock_target)
    client._client.on_message_callback('foobar')

    # assert
    mock_target.update_config.assert_called_with('foobar')
