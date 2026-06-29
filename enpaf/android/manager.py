"""
ENPAF Android — Manager base class
Common scaffolding for the per-capability modules (wifi, location, sensors,
nfc, audio, battery, notifications, device, permissions). Each manager exposes
a small set of simple methods and is reachable from JS via `enpaf.<name>.*`.

Most managers delegate to the tested DeviceAPI implementation (Android + dev
stubs); a few (bluetooth, wifi) are full standalone modules.
No third-party imports at module top level — this file is bundled into the APK.
"""

import logging

logger = logging.getLogger("enpaf.modules")


class Manager:
    """Base for a capability module. Subclasses set NAME and _ALLOWED and add
    methods; everything is dispatched through invoke()."""

    NAME = "module"
    _ALLOWED = set()

    def __init__(self, app):
        self._app = app
        self._api = getattr(app, "api", None)
        self._is_android = bool(getattr(app, "_is_android", False))

    def invoke(self, method, args=None):
        if method not in self._ALLOWED:
            raise ValueError(f"{self.NAME}: unknown method {method!r}")
        return getattr(self, method)(**(args or {}))

    def _fire(self, event, data=None):
        """Push an event to JS and Python handlers."""
        if self._app is None:
            return
        try:
            self._app.events.emit(event, data)
            self._app.bridge.emit_to_js(event, data)
        except Exception as e:
            logger.error(f"{self.NAME} emit error ({event}): {e}")

    def _ctx(self):
        from com.chaquo.python import Python
        return Python.getPlatform().getApplication()

    def _collect(self, item_event, finish_event, trigger, timeout=8.0):
        """Run an async operation and collect its result events synchronously.

        Used by the *_sync Python helpers so Python code can do e.g.
        `nets = app.wifi.scan_sync()["networks"]` without juggling events.
        """
        import threading
        items, done = [], threading.Event()

        def on_item(d):
            if d:
                items.append(d)

        def on_done(_d=None):
            done.set()

        ev = self._app.events
        ev.on(item_event, on_item)
        ev.on(finish_event, on_done)
        try:
            trigger()
            done.wait(max(0.5, float(timeout)))
        finally:
            ev.off(item_event, on_item)
            ev.off(finish_event, on_done)
        return items
