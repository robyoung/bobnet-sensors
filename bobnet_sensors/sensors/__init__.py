from abc import ABCMeta, abstractmethod
import asyncio
import importlib
import logging
import re

import bobnet_sensors

try:
    from gpiozero import MCP3008
    import RPi
except ImportError:
    # dummies for unit testing
    if not bobnet_sensors.TESTING:
        raise
    MCP3008 = None
    RPi = None

logger = logging.getLogger(__name__)


def parse_time(t):
    match = re.match(r'^(\d+(?:\.\d+)?)(s|m|h)$', t)
    if not match:
        raise ValueError(f'Invalid time format {t}')
    multipliers = {
        's': 1,
        'm': 60,
        'h': 60 * 60,
    }

    return float(match.group(1)) * multipliers[match.group(2)]


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
        try:
            for name, sensor_config in config['sensors'].items():
                sensor = self._sensors.get(name)
                if sensor:
                    ok, message = sensor.update_config(sensor_config)
                    if not ok:
                        errors.append(message)
        except Exception:
            errors.append('Invalid config')

        return (not bool(errors), errors)

    def __iter__(self):
        return (sensor for sensor in self._sensors.values())


def get_device_class(device):
    return importlib.import_module(f'.{device}', __package__).Device


class Sensor:
    @staticmethod
    def create(name, config):
        config = config.copy()
        device = config.pop('device')
        # TODO @robyoung remove this compatibility hack
        if device == 'MCP3008':
            device = 'mcp3008'
        every = config.pop('every', None)
        Device = get_device_class(device)
        return Sensor(name, every, Device(**config))

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
        logger.debug(f'update config on {self} with {config}')
        try:
            if config.get('every'):
                self._every = parse_time(config['every'])

            self.device.update_config(config)
            return (True, '')
        except Exception as e:
            return (False, str(e))

    async def run(self, looper):
        logger.debug(f'Starting {self}')
        while not looper.stopping:
            value = {
                'sensor': self.name,
                'value': self.device.value,
            }
            await looper.send_queue.put(value)
            logger.debug(f'Sent value {value}')
            await looper.wait_for(self.every)
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


def load_sensors(config):
    return Sensors.from_config(config)
