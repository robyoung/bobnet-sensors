import asyncio
from unittest import mock
from collections import namedtuple
import json

import pytest
import jwt

from bobnet_sensors import iotcore
from bobnet_sensors.models import ConfigMessage, CommandMessage

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
    looper, mock_mqtt, valid_config, private_key
):
    # act
    conn = iotcore.Connection.from_config(looper, valid_config)

    # assert
    assert conn.region == 'europe-west1'
    assert conn.private_key == private_key


def test_create_connection_from_config_fails_on_missing_keys(
    looper, mock_mqtt, valid_config
):
    # arrange
    del valid_config['iotcore']['region']

    # act and assert
    with pytest.raises(KeyError):
        iotcore.Connection.from_config(looper, valid_config)


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


@pytest.mark.parametrize('payload,expected_messages', [
    (
        {'devices': {'mydevice': {'foo': 'bar'}}},
        [ConfigMessage('mydevice', {'foo': 'bar'}), None]
    ),
    (
        {'commands': {'mydevice': {'id': 1,
                                   'state': 'new'}}},
        [CommandMessage('mydevice', 1, 'new', None), None]
    ),
    (
        {'devices': {'mydevice': {'foo': 'bar'}},
         'commands': {'mydevice': {'id': 1,
                                   'state': 'new'}}},
        [
            ConfigMessage('mydevice', {'foo': 'bar'}),
            CommandMessage('mydevice', 1, 'new', None),
            None,
        ]
    )
])
def test_on_message_sends_messages(
    payload, expected_messages, looper, iotcore_connection
):
    # arrange
    conn = iotcore_connection
    message = Message(json.dumps(payload).encode('utf8'))
    answers = []

    async def get_messages():
        while not looper.stopping:
            answers.append(await looper.config_queue.get())

    async def put_message():
        conn.on_message(None, None, message)
        await asyncio.sleep(0.01)
        looper.stop()

    # act
    looper.loop.run_until_complete(
        asyncio.gather(
            get_messages(),
            put_message(),
            loop=looper.loop
        )
    )

    # assert
    assert answers == expected_messages


def test_on_message_sends_no_message_if_no_payload(
    looper, iotcore_connection
):
    # arrange
    conn = iotcore_connection
    message = Message(''.encode('utf8'))
    answers = []

    async def get_message():
        answers.append(await looper.config_queue.get())

    async def put_message():
        conn.on_message(None, None, message)
        await asyncio.sleep(0.001)
        looper.stop()

    # act
    looper.loop.run_until_complete(
        asyncio.gather(
            get_message(),
            put_message(),
            loop=looper.loop
        )
    )

    # assert
    assert answers == [None]


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
def test_load_iotcore(mock_Connection, looper):
    # arrange
    mock_connect = mock.Mock()

    mock_Connection.from_config.return_value.connect = mock_connect

    # act
    client = iotcore.load_iotcore(looper, {})

    # assert
    assert client._client == mock_Connection.from_config.return_value


def test_run_send_stop_no_value(looper):
    async def do_task(looper):
        looper.stop()

    mock_client = mock.Mock()

    client = iotcore.IOTCoreClient(mock_client)

    looper.loop.run_until_complete(
        asyncio.gather(
            client.run_send(looper),
            do_task(looper),
            loop=looper.loop
        )
    )

    assert not mock_client.publish.called


def test_run_send_value_then_stop(looper):
    async def do_task(looper):
        await looper.send_queue.put('test value')
        await asyncio.sleep(0.0001)
        looper.stop()

    mock_client = mock.Mock()
    mock_client._wait_for_connection = return_immediately

    client = iotcore.IOTCoreClient(mock_client)

    looper.loop.run_until_complete(
        asyncio.gather(
            client.run_send(looper),
            do_task(looper),
            loop=looper.loop
        )
    )

    mock_client.publish.assert_called_with('test value')
