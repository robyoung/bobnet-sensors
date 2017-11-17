from abc import ABCMeta, abstractmethod
import asyncio
import logging
import re

try:
    from gpiozero import MCP3008
except ImportError:
    MCP3008 = None  # dummy for unit testing

logger = logging.getLogger(__name__)


def parse_time(t):
    match = re.match(r'^(\d+)(s|m|h)$', t)
    if not match:
        raise ValueError(f'Invalid time format {t}')
    multipliers = {
        's': 1,
        'm': 60,
        'h': 60 * 60,
    }

    return int(match.group(1)) * multipliers[match.group(2)]


class Sensors:
    @staticmethod
    def from_config(config):
        sensor_configs = config['sensors']
        sensors = {}
        for name, sensor_config in sensor_configs.items():
            sensors[name] = Sensor.create(name, sensor_config)

        return Sensors(sensors)

    def __init__(self, sensors):
        self._sensors = sensors

    def update_config(self, config):
        errors = []
        for name, sensor_config in config['sensors'].items():
            if name in self._sensors:
                ok, message = self._sensors[name].update_config(sensor_config)
                if not ok:
                    errors.append(message)

        return (not bool(errors), errors)

    def __iter__(self):
        return (sensor for sensor in self._sensors.values())


class Sensor:
    @staticmethod
    def create(name, config):
        config = config.copy()
        device = config.pop('device')
        every = config.pop('every', None)
        return Sensor(name, every, DEVICE_CLASSES[device](**config))

    def __init__(self, name, every, device):
        self._name = name
        self._every = parse_time(every or '30s')
        self._device = device
        logger.debug(
            f'Created {self} values every {self.every}s from {self.device}')

    @property
    def name(self):
        return self._name

    @property
    def every(self):
        return self._every

    @property
    def device(self):
        return self._device

    def update_config(self, config):
        try:
            if config.get('every'):
                self._every = parse_time(config['every'])

            self.device.update_config(config)
            return (True, '')
        except Exception as e:
            return (False, str(e))

    async def run(self, stop, values):
        logger.debug(f'Starting {self}')
        while not stop.is_set():
            value = {
                'sensor': self.name,
                'value': self.device.value,
            }
            await values.put(value)
            logger.debug(f'Sent value {value}')
            try:
                await asyncio.wait_for(stop.wait(), self.every)
            except asyncio.TimeoutError:
                pass
        logger.debug(f'Stopping {self}')

    def __repr__(self):
        return f'<Sensor name={self.name}>'


class BaseDevice(metaclass=ABCMeta):
    @property
    @abstractmethod
    def value(self):
        pass

    def update_config(self, config):
        pass


class MCP3008Device(BaseDevice):
    def __init__(self, channel):
        self._channel = channel
        self._mcp3008 = MCP3008(
            channel=self._channel,
            clock_pin=18,
            mosi_pin=24, miso_pin=23, select_pin=25
        )

    @property
    def value(self):
        return self._mcp3008.value

    def __repr__(self):
        return f'<MCP3008Device channel={self._channel}>'


DEVICE_CLASSES = {
    'MCP3008': MCP3008Device,
}


def load_sensors(config):
    return Sensors.from_config(config)