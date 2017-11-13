from bobnet_sensors import config


def test_load_config():
    c = config.load_config('./tests/fixtures/config.yml')

    assert 'sensors' in c
    assert 'iotcore' in c
