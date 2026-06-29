"""ENPAF Android — Location module (geolocation)."""

from enpaf.android.manager import Manager


class LocationManager(Manager):
    NAME = "location"
    _ALLOWED = {"get", "last_known", "is_available"}

    def get(self, **kw):
        """Most recent known location {latitude, longitude, accuracy, ...}."""
        return self._api.get_location(**kw)

    def last_known(self, **kw):
        return self._api.get_location(**kw)

    def is_available(self, **_):
        loc = self._api.get_location()
        return {"available": bool(loc.get("available")), "fix": bool(loc.get("fix"))}
