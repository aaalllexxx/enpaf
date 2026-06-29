"""ENPAF Android — Battery & network module."""

from enpaf.android.manager import Manager


class BatteryManager(Manager):
    NAME = "battery"
    _ALLOWED = {"info", "network"}

    def info(self, **_):
        """Battery level + charging state {level, charging}."""
        return self._api.get_battery()

    def network(self, **_):
        """Connectivity info {connected, type}."""
        return self._api.get_network()
