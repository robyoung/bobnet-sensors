import asyncio


def run(looper, iotcore, sensors):
    iotcore.setup_config_handler(sensors)
    iotcore.start()

    sensor_tasks = [
        sensor.run(looper) for sensor in sensors
    ]
    iotcore_tasks = [
        iotcore.run_send(looper),
    ]
    all_tasks = sensor_tasks + iotcore_tasks

    looper.loop.run_until_complete(
        asyncio.gather(
            *all_tasks,
            loop=looper.loop
        )
    )
