import logging
from datetime import datetime, timedelta
import re


class BaseMessage:
    _PATTERN1 = re.compile('Message$')
    _PATTERN2 = re.compile('(?<!^)(?<![A-Z])([A-Z])')

    @property
    def type(self):
        return self._PATTERN2.sub(
            r'_\1',
            self._PATTERN1.sub(
                '',
                self.__class__.__name__
            )
        ).lower()

    def as_json(self):
        return {**{
            'type': self.type
        }, **self.__dict__}

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__
        )


class ConfigMessage(BaseMessage):
    def __init__(self, device, config):
        self.device = device
        self.config = config


class CommandMessage(BaseMessage):
    @classmethod
    def from_dict(cls, device, command):
        timestamp = None
        if command.get('timestamp'):
            timestamp = datetime.strptime(
                command['timestamp'],
                '%Y-%m-%dT%H:%M:%S.%fZ')

        return cls(
            device,
            command['id'],
            command['state'],
            timestamp
        )

    def __init__(self, device, id, state, timestamp):
        self.device = device
        self.id = id
        self.state = state
        self.timestamp = timestamp

    @property
    def should_run(self):
        if self.state == 'new':
            return True
        elif self.state == 'ack':
            return self.timestamp <= datetime.utcnow() - timedelta(hours=2)

    def ack(self):
        return CommandMessage(self.device, self.id, 'ack', datetime.utcnow())


class DataMessage(BaseMessage):
    def __init__(self, device, data):
        self.device = device
        self.data = data


class CommandResponseMessage(BaseMessage):
    def __init__(self, device, id, state):
        self.device = device
        self.id = id
        self.state = state  # TODO validate


class LogMessage(BaseMessage):
    @classmethod
    def error(cls, message):
        return LogMessage(message, level=logging.ERROR)

    def __init__(self, message, level):
        self.message = message
        self.level = logging.getLevelName(level).lower()
