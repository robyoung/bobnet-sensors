import asyncio


def run(looper, iotcore, sensors):
    iotcore.start()

    sensor_tasks = [
        sensor.run(looper) for sensor in sensors
    ]
    sensor_config_tasks = [
        sensors.run_update_config(looper)
    ]
    iotcore_tasks = [
        iotcore.run_send(looper),
    ]
    all_tasks = sensor_tasks + sensor_config_tasks + iotcore_tasks

    looper.loop.run_until_complete(
        asyncio.gather(
            *all_tasks,
            loop=looper.loop
        )
    )
