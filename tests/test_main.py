import asyncio
from unittest import mock

from bobnet_sensors.main import run


async def send_one_value_then_stop(loop, stop, values):
    await values.put('one value')
    await asyncio.sleep(0.01, loop=loop)
    stop.set()


async def do_nothing(loop, stop, values):
    pass


def test_run_immediately_stop(loop, stop, sensors, iotcore_client):
    stop.set()
    sensors.update_config = mock.Mock()
    iotcore_client.send = mock.Mock()

    run(loop, stop, iotcore_client, sensors)

    assert not sensors.update_config.called
    assert not iotcore_client.send.called


def test_run_with_one_value(loop, stop, sensors, iotcore_client):
    sensors.update_config = mock.Mock()
    iotcore_client.send = mock.Mock()
    sensors._sensors['sensor1'].run = send_one_value_then_stop
    sensors._sensors['sensor2'].run = do_nothing

    run(loop, stop, iotcore_client, sensors)

    assert not sensors.update_config.called
    iotcore_client.send.assert_called_with('one value')
