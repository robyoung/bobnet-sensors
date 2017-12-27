from bobnet_sensors.sensors.counter import Device as CounterDevice


def test_counter_value_increases():
    counter = CounterDevice()

    assert counter.value == 0
    assert counter.value == 1
    assert counter.value == 2


def test_counter_with_alternative_start():
    counter = CounterDevice(start=3)

    assert counter.value == 3
    assert counter.value == 4


def test_counter_repr_does_not_affect_value():
    counter = CounterDevice()

    assert str(counter) == '<counter.Device count=0>'
    assert counter.value == 0
