import pytest
from unittest import mock

from bobnet_sensors.sensors.envirophat import Device as EnvirophatDevice


@pytest.fixture
def mock_envirophat():
    with mock.patch('bobnet_sensors.sensors.envirophat.envirophat') as m:
        yield m


def test_create_envirophat_with_single_sensor(mock_envirophat):
    d = EnvirophatDevice(sensor='weather.temperature')

    assert d.sensors == ['weather.temperature']


def test_create_envirophat_with_multiple_sensors(mock_envirophat):
    d = EnvirophatDevice(sensors=['weather.temperature', 'weather.pressure'])

    assert d.sensors == ['weather.temperature', 'weather.pressure']


def test_create_envirophat_fails_with_no_args(mock_envirophat):
    with pytest.raises(ValueError):
        EnvirophatDevice()


def test_create_envirophat_fails_with_empty_sensors(mock_envirophat):
    with pytest.raises(ValueError):
        EnvirophatDevice(sensors=[])


@pytest.mark.parametrize('sensor', [
    'light.rgb',
    'light.light',
    'weather.temperature',
    'weather.pressure',
    'weather.altitude',
])
def test_create_envirophat_with_valid_sensors(sensor):
    d = EnvirophatDevice(sensor=sensor)

    assert d.sensors == [sensor]


@pytest.mark.parametrize('sensor', [
    'light.invalid',
    'invalid.light',
    'badparse',
    1234,
    'light.light.light',
])
def test_create_envirophat_fails_with_invalid_sensors(sensor):
    with pytest.raises(ValueError):
        EnvirophatDevice(sensor=sensor)


def test_value_returns_dict_for_multiple_sensors(mock_envirophat):
    mock_envirophat.weather.temperature.return_value = 123
    mock_envirophat.light.light.return_value = 321
    d = EnvirophatDevice(sensors=['weather.temperature', 'light.light'])

    assert d.value == {'weather.temperature': 123, 'light.light': 321}


def test_value_returns_value_for_single_sensor(mock_envirophat):
    mock_envirophat.light.light.return_value = 123
    d = EnvirophatDevice(sensor='light.light')

    assert d.value == 123


def test_update_config_set_led_on(mock_envirophat):
    d = EnvirophatDevice(sensor='light.light')
    d.update_config({'leds': 'on'})

    assert mock_envirophat.leds.on.called
    assert not mock_envirophat.leds.off.called


def test_update_config_set_led_off(mock_envirophat):
    d = EnvirophatDevice(sensor='light.light')
    d.update_config({'leds': 'off'})

    assert not mock_envirophat.leds.on.called
    assert mock_envirophat.leds.off.called
