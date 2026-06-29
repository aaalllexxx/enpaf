"""
ENPAF Core — Python ↔ JS Bridge
Handles communication between Python backend and JavaScript frontend.
In dev mode: uses WebSocket via Flask-SocketIO.
On Android: uses JavaScriptInterface callbacks.
"""

import json
import logging
import threading
import uuid
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("enpaf.bridge")


class Bridge:
    """
    Python ↔ JavaScript bridge.
    
    Registers Python functions that can be called from JS,
    and allows Python to call JS functions / emit events.
    
    Usage:
        bridge = Bridge()
        
        @bridge.register("get_users")
        def get_users(params):
            return [{"name": "Alex"}]
        
        # Called when JS does: enpaf.call("get_users", {})
    """

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._event_handlers: Dict[str, list] = {}
        self._socketio = None
        self._lock = threading.Lock()
        self._pending_responses: Dict[str, Any] = {}
        # Android-only: (activity, webview) so Python can push events into the
        # WebView's JS. Stays None in dev mode (SocketIO is used instead).
        self._android_activity = None
        self._android_webview = None

    def register(self, name: str, handler: Callable = None) -> Callable:
        """
        Register a Python function callable from JavaScript.
        
        Can be used as a decorator:
            @bridge.register("get_data")
            def get_data(params):
                return {"result": "ok"}
        
        Or directly:
            bridge.register("get_data", my_handler)
        """
        if handler is not None:
            self._handlers[name] = handler
            logger.debug(f"Bridge: registered handler '{name}'")
            return handler

        def decorator(func: Callable) -> Callable:
            self._handlers[name] = func
            logger.debug(f"Bridge: registered handler '{name}'")
            return func
        return decorator

    def unregister(self, name: str) -> None:
        """Remove a registered handler."""
        self._handlers.pop(name, None)

    def set_socketio(self, socketio):
        """Set the SocketIO instance for dev mode communication."""
        self._socketio = socketio

    def set_android_webview(self, activity, webview):
        """Wire the Android Activity + WebView so Python can emit events to JS.

        On Android there is no SocketIO; Python pushes events by evaluating
        `window.__enpaf_event(...)` in the WebView on the UI thread.
        """
        self._android_activity = activity
        self._android_webview = webview

    def handle_call(self, name: str, params: dict = None, call_id: str = None) -> dict:
        """
        Handle an incoming call from JavaScript.
        Returns a response dict with {success, data/error, callId}.
        """
        if params is None:
            params = {}

        if name not in self._handlers:
            error_msg = f"Bridge handler '{name}' not found"
            logger.warning(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "callId": call_id,
            }

        try:
            handler = self._handlers[name]
            result = handler(params)
            return {
                "success": True,
                "data": result,
                "callId": call_id,
            }
        except Exception as e:
            error_msg = f"Bridge handler '{name}' error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "callId": call_id,
            }

    def emit_to_js(self, event: str, data: Any = None) -> None:
        """
        Emit an event to JavaScript side.
        In dev mode, uses SocketIO.
        """
        if self._socketio:
            self._socketio.emit("enpaf_event", {
                "event": event,
                "data": data,
            })
            logger.debug(f"Bridge: emitted event '{event}' to JS")
        elif self._android_webview is not None and self._android_activity is not None:
            self._emit_to_webview(event, data)
        else:
            logger.debug(f"Bridge: event '{event}' (no JS target connected)")

    def _emit_to_webview(self, event: str, data: Any) -> None:
        """Android: run window.__enpaf_event(event, dataJson) in the WebView."""
        try:
            data_json = json.dumps(data, ensure_ascii=False) if data is not None else "{}"
            js = "window.__enpaf_event(%s, %s)" % (json.dumps(event), json.dumps(data_json))
            webview = self._android_webview
            from java import dynamic_proxy
            from java.lang import Runnable

            class _Emit(dynamic_proxy(Runnable)):
                def run(self):
                    webview.evaluateJavascript(js, None)

            self._android_activity.runOnUiThread(_Emit())
        except Exception as e:
            logger.error(f"Bridge: emit_to_webview error: {e}")

    def on_js_event(self, event: str, handler: Callable) -> Callable:
        """Register a handler for events coming from JavaScript."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
        return handler

    def handle_js_event(self, event: str, data: Any = None) -> None:
        """Process an incoming event from JavaScript."""
        handlers = self._event_handlers.get(event, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Bridge event handler error ({event}): {e}", exc_info=True)

    def get_registered_handlers(self) -> list:
        """Get list of all registered handler names."""
        return list(self._handlers.keys())

    def call_native(self, method: str, params: dict) -> Any:
        """
        Call a native Android method (only works on Android).
        In dev mode, this is a no-op that logs the call.
        """
        logger.info(f"Bridge: native call '{method}' with params {params}")
        return None
