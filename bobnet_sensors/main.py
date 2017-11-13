
def run(iotcore, sensors):
    for message in sensors.read():
        iotcore.send(message)

        # Keep it simple to start with
        if iotcore.has_new_config:
            sensors.update_config(iotcore.config)
