import asyncio
from unittest import mock

from bobnet_sensors.main import run


async def send_one_value_then_stop(looper):
    await looper.send_queue.put('one value')
    await asyncio.sleep(0.01, loop=looper.loop)
    looper.stop()


async def do_nothing(looper):
    pass


def test_run_immediately_stop(looper, sensors, iotcore_client):
    looper.stop()
    sensors.update_config = mock.Mock()
    iotcore_client.send = mock.Mock()

    run(looper, iotcore_client, sensors)

    assert not sensors.update_config.called
    assert not iotcore_client.send.called


def test_run_with_one_value(looper, sensors, iotcore_client):
    sensors.update_config = mock.Mock()
    iotcore_client.send = mock.Mock()
    sensors._sensors['sensor1'].run = send_one_value_then_stop
    sensors._sensors['sensor2'].run = do_nothing

    run(looper, iotcore_client, sensors)

    assert not sensors.update_config.called
    iotcore_client.send.assert_called_with('one value')
