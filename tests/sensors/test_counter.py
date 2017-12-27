from bobnet_sensors.sensors.counter import Device as CounterDevice


def test_counter_value_increases():
    counter = CounterDevice()

    assert counter.value == {'count': 0}
    assert counter.value == {'count': 1}
    assert counter.value == {'count': 2}


def test_counter_with_alternative_start():
    counter = CounterDevice(start=3)

    assert counter.value == {'count': 3}
    assert counter.value == {'count': 4}


def test_counter_repr_does_not_affect_value():
    counter = CounterDevice()

    assert str(counter) == '<counter.Device count=0>'
    assert counter.value == {'count': 0}
