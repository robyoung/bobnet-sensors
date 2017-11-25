import functools
import logging

from . import BaseDevice

try:
    import envirophat
except ImportError:
    # dummies for unit testing
    envirophat = None

logger = logging.getLogger(__name__)


@functools.singledispatch
def read_sensor_value(sensor):
    module, method = sensor.split('.')
    return {
        sensor: getattr(getattr(envirophat, module), method)()
    }


@read_sensor_value.register(dict)
def _(sensor):
    name = sensor['sensor']
    label = sensor['label']

    return {label: read_sensor_value(name)[name]}


@functools.singledispatch
def validate_sensor(sensor):
    allowed = {
        'light': ['rgb', 'light'],
        'weather': ['temperature', 'pressure', 'altitude'],
    }
    try:
        parts = sensor.split('.', maxsplit=1)
    except AttributeError:
        raise ValueError
    if len(parts) != 2:
        raise ValueError
    if parts[0] not in allowed:
        raise ValueError
    if parts[1] not in allowed[parts[0]]:
        raise ValueError
    if parts[0] not in ['light', 'weather']:
        raise ValueError


@validate_sensor.register(dict)
def _(sensor):
    validate_sensor(sensor.get('sensor'))
    if not isinstance(sensor.get('label'), str):
        raise ValueError


class Device(BaseDevice):
    def __init__(self, sensor=None, sensors=None):
        if sensor is not None:
            self.sensors = [sensor]
        elif sensors:
            self.sensors = sensors
        else:
            raise ValueError
        list(map(validate_sensor, self.sensors))

    @property
    def value(self):
        values = [
            read_sensor_value(sensor) for sensor in self.sensors
        ]
        result = {}
        for value in values:
            result = dict(result, **value)
        return result

    def update_config(self, config):
        if config.get('leds') == 'on':
            envirophat.leds.on()
        elif config.get('leds') == 'off':
            envirophat.leds.off()

    def __repr__(self):
        return f'<envirophat.Device>'
