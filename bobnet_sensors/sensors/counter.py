from . import BaseDevice


class Device(BaseDevice):
    def __init__(self, start=0):
        self._count = start

    @property
    def value(self):
        v = self._count
        self._count += 1
        return v

    def __repr__(self):
        return f'<counter.Device count={self.value}>'
