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


class Device(BaseDevice):
    def __init__(self, channel):
        self._channel = channel
        RPi.GPIO.setmode(RPi.GPIO.BCM)
        self._mcp3008 = MCP3008(
            channel=self._channel,
            clock_pin=18,
            mosi_pin=24, miso_pin=23, select_pin=25
        )

    @property
    def value(self):
        return self._mcp3008.value

    def __repr__(self):
        return f'<mcp3008.Device channel={self._channel}>'
