from datetime import datetime, timedelta

import pytest

from conftest import roughly

from bobnet_sensors.models import (
    ConfigMessage,
    CommandMessage,
    CommandResponseMessage,
    DataMessage,
    LogMessage
)


@pytest.mark.parametrize('message,expected_type', [
    (ConfigMessage('d', {'f': 1}), 'config'),
    (CommandMessage('d', 1, 'new', None), 'command'),
    (DataMessage('d', {}), 'data'),
    (CommandResponseMessage('d', 1, 'new'), 'command_response'),
    (LogMessage.error('hi'), 'log'),
])
def test_message_type(message, expected_type):
    assert message.type == expected_type


@pytest.mark.parametrize('message,expected_json', [
    (
        DataMessage('mydevice', {'foo': 'bar'}),
        {'type': 'data',
         'device': 'mydevice',
         'data': {'foo': 'bar'}}
    ),
    (
        CommandResponseMessage('mydevice', 1, 'new'),
        {'type': 'command_response',
         'device': 'mydevice',
         'id': 1,
         'state': 'new'}
    ),
    (
        LogMessage.error('hi'),
        {'type': 'log',
         'level': 'error',
         'message': 'hi'}
    )
])
def test_message_as_json(message, expected_json):
    assert message.as_json() == expected_json


@pytest.mark.parametrize('command,expected_should_run', [
    (CommandMessage('d', 1, 'new', datetime.utcnow()), True),
    (CommandMessage('d', 1, 'ack', datetime.utcnow()), False),
    (CommandMessage('d', 1, 'ack', datetime.utcnow() - timedelta(hours=2)),
     True)
])
def test_command_message_should_run(command, expected_should_run):
    assert command.should_run == expected_should_run


@pytest.mark.parametrize('command_dict,expected_command', [
    (
        {'id': 1, 'state': 'new'},
        CommandMessage('mydevice', 1, 'new', None)
    ),
    (
        {'id': 1, 'state': 'new', 'timestamp': None},
        CommandMessage('mydevice', 1, 'new', None)
    ),
    (
        {'id': 1, 'state': 'new', 'timestamp': '2012-12-12T12:12:12.0012Z'},
        CommandMessage('mydevice', 1, 'new',
                       datetime(2012, 12, 12, 12, 12, 12, 1200))
    )
])
def test_command_message_from_dict(command_dict, expected_command):
    command = CommandMessage.from_dict('mydevice', command_dict)
    assert command == expected_command


def test_command_message_ack():
    command = CommandMessage('mydevice', 1, 'new', None)
    assert command.ack() == CommandMessage('mydevice', 1, 'ack',
                                           roughly(datetime.utcnow()))
