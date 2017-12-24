import asyncio


def run(loop, stop, iotcore, sensors):
    values = asyncio.Queue(loop=loop)

    iotcore.setup_config_handler(sensors)
    iotcore.start()

    sensor_tasks = [sensor.run(loop, stop, values) for sensor in sensors]
    iotcore_tasks = [
        iotcore.run_send(loop, stop, values),
    ]
    all_tasks = sensor_tasks + iotcore_tasks

    loop.run_until_complete(asyncio.gather(*all_tasks, loop=loop))
