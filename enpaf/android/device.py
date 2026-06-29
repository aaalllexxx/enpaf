"""ENPAF Android — Device module (info, vibrate, toast, clipboard, share, ...)."""

from enpaf.android.manager import Manager


class DeviceManager(Manager):
    NAME = "device"
    _ALLOWED = {
        "info", "vibrate", "toast", "share", "open_url",
        "clipboard_get", "clipboard_set", "set_orientation",
    }

    def info(self, **_):
        return self._api.get_device_info()

    def vibrate(self, milliseconds=100, **_):
        self._api.vibrate(milliseconds)
        return {"ok": True}

    def toast(self, message="", duration="short", **_):
        self._api.toast(message, duration)
        return {"ok": True}

    def share(self, text="", title="", **_):
        self._api.share(text, title)
        return {"ok": True}

    def open_url(self, url="", **_):
        self._api.open_url(url)
        return {"ok": True}

    def clipboard_get(self, **_):
        return {"text": self._api.clipboard_get()}

    def clipboard_set(self, text="", **_):
        self._api.clipboard_set(text)
        return {"ok": True}

    def set_orientation(self, orientation="auto", **_):
        self._api.set_orientation(orientation)
        return {"ok": True}
