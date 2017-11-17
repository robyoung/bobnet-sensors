import asyncio
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
    # act
    conn = iotcore.Connection.from_config(valid_config)

    # assert
    assert conn.region == 'europe-west1'
    assert conn.private_key == private_key


def test_create_connection_from_config_fails_on_missing_keys(
    mock_mqtt, valid_config
):
    # arrange
    del valid_config['iotcore']['region']

    # act and assert
    with pytest.raises(KeyError):
        iotcore.Connection.from_config(valid_config)


def test_connection_connect(mock_mqtt_client, iotcore_connection):
    # arrange
    conn = iotcore_connection
    mock_connect_event = mock.Mock()
    mock_connect_event.wait.return_value = True
    conn.connect_event = mock_connect_event

    # act
    conn.connect()

    # assert
    assert mock_mqtt_client.connect.called
    assert mock_mqtt_client.loop_start.called
    assert mock_connect_event.wait.called
    mock_mqtt_client.subscribe.assert_called_with('/devices/test01/config',
                                                  qos=1)


def test_on_connect_event(mock_mqtt_client, iotcore_connection):
    # arrange
    conn = iotcore_connection
    conn.connect_event = mock.Mock()

    # act
    conn.on_connect(None, None, None, None)

    # assert
    assert mock_mqtt_client.on_connect == conn.on_connect
    assert conn.connected
    assert conn.connect_event.set.called


def test_on_disconnect_event(mock_mqtt_client, iotcore_connection):
    # arrange
    conn = iotcore_connection
    conn.connect_event = mock.Mock()

    # act
    conn.on_disconnect(None, None, None)

    # assert
    assert mock_mqtt_client.on_disconnect == conn.on_disconnect
    assert not conn.connected
    assert conn.connect_event.clear.called


def test_on_subscribe_fails_on_qos_failure(iotcore_connection):
    # arrange
    conn = iotcore_connection

    # act and assert
    with pytest.raises(RuntimeError):
        conn.on_subscribe(None, None, None, (128,))


Message = namedtuple('Message', 'payload')


def test_on_message_sets_message(iotcore_connection):
    # arrange
    conn = iotcore_connection
    message = Message('{"foo": "bar"}'.encode('utf8'))

    # act
    conn.on_message(None, None, message)

    # assert
    assert conn.message == {'foo': 'bar'}
    assert conn.has_message_event.is_set()
    assert conn.new_message_event.is_set()


def test_on_message_sets_no_message_if_no_payload(iotcore_connection):
    # arrange
    conn = iotcore_connection
    message = Message(''.encode('utf8'))

    # act
    conn.on_message(None, None, message)

    # assert
    assert not conn.has_message_event.is_set()
    assert not conn.new_message_event.is_set()


def test_publish_message(mock_mqtt_client, iotcore_connection):
    # arrange
    conn = iotcore_connection

    # act
    conn.publish({'foo': 'bar'})

    # assert
    mock_mqtt_client.publish.assert_called_once_with(
        '/devices/test01/events', '{"foo": "bar"}',
        qos=1)


@mock.patch('bobnet_sensors.iotcore.Connection')
def test_load_iotcore(mock_Connection):
    # act
    client = iotcore.load_iotcore({})
    client.send('message')

    # assert
    assert mock_Connection.from_config.return_value.connect.called


def test_run_send_stop_no_value():
    loop = asyncio.new_event_loop()
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


def test_run_send_value_then_stop():
    loop = asyncio.new_event_loop()
    stop = asyncio.Event(loop=loop)
    values = asyncio.Queue(loop=loop)

    async def test_task(stop, values):
        await values.put('test value')
        await asyncio.sleep(0.0001)
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

    mock_client.publish.assert_called_with('test value')


def test_run_config_stop_no_config():
    loop = asyncio.new_event_loop()
    stop = asyncio.Event(loop=loop)
    target = mock.Mock()

    mock_client = mock.Mock()
    mock_client.new_message_event = asyncio.Event(loop=loop)
    client = iotcore.IOTCoreClient(mock_client)

    async def test_task(stop, mock_client):
        stop.set()

    loop.run_until_complete(
        asyncio.gather(
            client.run_config(loop, stop, target),
            test_task(stop, mock_client),
            loop=loop
        )
    )

    assert not target.update_config.called


def test_run_config_with_config_then_stop():
    loop = asyncio.new_event_loop()
    stop = asyncio.Event(loop=loop)
    target = mock.Mock()
    target.update_config.return_value = (True, '')

    mock_client = mock.Mock()
    mock_client.new_message_event = asyncio.Event(loop=loop)
    mock_client.message = 'test message'
    client = iotcore.IOTCoreClient(mock_client)

    async def test_task(stop, mock_client):
        mock_client.new_message_event.set()
        await asyncio.sleep(0.01)
        stop.set()

    loop.run_until_complete(
        asyncio.gather(
            client.run_config(loop, stop, target),
            test_task(stop, mock_client),
            loop=loop
        )
    )

    target.update_config.assert_called_with('test message')
