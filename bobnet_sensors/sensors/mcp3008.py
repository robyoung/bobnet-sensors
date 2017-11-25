import logging

from . import BaseDevice

try:
    from gpiozero import MCP3008
    import RPi
except ImportError:
    # dummies for unit testing
    MCP3008 = None
    RPi = None


logger = logging.getLogger(__name__)


def validate_channel(channel):
    try:
        c = int(channel.get('channel'))
        if c < 0 or c > 8:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError(f'Invalid channel {channel.get("channel")}')
    if not isinstance(channel.get('label'), str):
        raise ValueError('Label not set')


def read_channel_value(channel):
    return {
        channel['label']: channel['client'].value
    }


class Device(BaseDevice):
    def __init__(self, channels):
        if not channels:
            raise ValueError('No channels')
        list(map(validate_channel, channels))
        if len(set(c['channel'] for c in channels)) != len(channels):
            raise ValueError('Duplicate channels used')

        self.channels = channels

        RPi.GPIO.setmode(RPi.GPIO.BCM)
        for channel in self.channels:
            channel['client'] = MCP3008(
                channel=channel['channel'],
                clock_pin=18,
                mosi_pin=24, miso_pin=23, select_pin=25
            )

    @property
    def value(self):
        values = [
            read_channel_value(channel) for channel in self.channels
        ]
        result = {}
        for value in values:
            result.update(value)
        return result

    def __repr__(self):
        return f'<mcp3008.Device with {len(self.channels)} channels>'
