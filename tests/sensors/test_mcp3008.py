from unittest import mock

import pytest

from bobnet_sensors.sensors.mcp3008 import Device as MCP3008Device


@pytest.mark.parametrize('channel', [
    {'channel': '1', 'label': 'light'},
    {'channel': '0', 'label': 'light'},
    {'channel': '8', 'label': 'light'},
    {'channel': 1, 'label': 'light'},
    {'channel': 0, 'label': 'light'},
    {'channel': 8, 'label': 'light'},
])
def test_create_mcp3008_with_valid_channels(channel):
    MCP3008Device([channel])


@pytest.mark.parametrize('channel', [
    {'channel': -1, 'label': 'light'},
    {'channel': 9, 'label': 'light'},
    {'channel': 'blah', 'label': 'light'},
    {},
    {'label': 'light'},
    {'channel': 0},
    {'channel': 0, 'label': None},
])
def test_create_mcp3008_fails_with_invalid_channels(channel):
    with pytest.raises(ValueError):
        MCP3008Device([channel])


def test_create_mcp3008_fails_with_no_channels():
    with pytest.raises(ValueError):
        MCP3008Device([])


def test_read_values(mock_mcp3008):
    clients = [
        mock.Mock(),
        mock.Mock(),
    ]
    mock_mcp3008.side_effect = clients
    clients[0].value = 123
    clients[1].value = 321
    channels = [
        {'channel': 0, 'label': 'temp'},
        {'channel': 1, 'label': 'light'},
    ]
    device = MCP3008Device(channels)

    assert device.value == {
        'temp': 123,
        'light': 321,
    }


def test_gpio_mode_is_set(mock_RPi):
    mock_RPi.GPIO.BCM = 'bcm'

    MCP3008Device([{'channel': 0, 'label': 'temp'}])

    mock_RPi.GPIO.setmode.assert_called_with('bcm')
