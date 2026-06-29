"""ENPAF Android — Sensors module (accelerometer, gyroscope, light, ...)."""

from enpaf.android.manager import Manager


class SensorsManager(Manager):
    NAME = "sensors"
    _ALLOWED = {
        "read", "list", "snapshot", "accelerometer", "gyroscope",
        "magnetometer", "light", "proximity", "pressure",
    }

    def read(self, sensor="accelerometer", **kw):
        return self._api.read_sensor(sensor=sensor, **kw)

    def list(self, **_):
        return self._api.list_sensors()

    def snapshot(self, **_):
        return self._api.get_sensor_snapshot()

    def accelerometer(self, **_): return self._api.read_sensor("accelerometer")
    def gyroscope(self, **_): return self._api.read_sensor("gyroscope")
    def magnetometer(self, **_): return self._api.read_sensor("magnetometer")
    def light(self, **_): return self._api.read_sensor("light")
    def proximity(self, **_): return self._api.read_sensor("proximity")
    def pressure(self, **_): return self._api.read_sensor("pressure")
