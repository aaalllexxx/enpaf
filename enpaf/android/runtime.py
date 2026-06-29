"""
ENPAF Android — Runtime
Manages the Python interpreter and bridge on Android.
This module runs inside the APK via Chaquopy's embedded Python.
"""

import json
import logging
from typing import Any

logger = logging.getLogger("enpaf.android.runtime")


class AndroidRuntime:
    """
    Android runtime that connects the Python app logic
    to the Java WebView via Chaquopy bridge.
    
    This class is instantiated by MainActivity.java when the app starts.
    """

    def __init__(self, app_instance):
        """
        Args:
            app_instance: The EnpafApp instance
        """
        self.app = app_instance
        self._activity = None
        self._webview = None

    def set_activity(self, activity):
        """Set the Android Activity reference (called from Java)."""
        self._activity = activity

    def set_webview(self, webview):
        """Set the WebView reference (called from Java)."""
        self._webview = webview

    def start(self):
        """Start the runtime (called after Activity is created)."""
        logger.info("ENPAF Android Runtime starting...")
        self.app.events.emit("app_start")

    def stop(self):
        """Stop the runtime (called when Activity is destroyed)."""
        self.app.events.emit("app_stop")
        self.app.storage.close()

    def pause(self):
        """Called when the app is paused."""
        self.app.events.emit("app_pause")

    def resume(self):
        """Called when the app is resumed."""
        self.app.events.emit("app_resume")

    def handle_bridge_call(self, name: str, params_json: str, call_id: str) -> str:
        """
        Handle a bridge call from JavaScript (via JavaScriptInterface).
        Called from Java on the WebView thread.
        
        Args:
            name: Handler name
            params_json: JSON string of parameters
            call_id: Unique call identifier
            
        Returns:
            JSON string with the response
        """
        try:
            params = json.loads(params_json) if params_json else {}
        except json.JSONDecodeError:
            params = {}

        response = self.app.bridge.handle_call(name, params, call_id)
        return json.dumps(response, ensure_ascii=False)

    def handle_event(self, event: str, data_json: str):
        """
        Handle an event from JavaScript.
        
        Args:
            event: Event name
            data_json: JSON string of event data
        """
        try:
            data = json.loads(data_json) if data_json else None
        except json.JSONDecodeError:
            data = data_json

        self.app.bridge.handle_js_event(event, data)
        self.app.events.emit(event, data)

    def emit_to_webview(self, event: str, data: Any = None):
        """
        Emit an event to the WebView JavaScript.
        Runs JavaScript code in the WebView on the UI thread.
        """
        if self._webview and self._activity:
            data_json = json.dumps(data, ensure_ascii=False) if data is not None else '{}'
            js_code = f"window.__enpaf_event('{event}', '{data_json}')"

            def run_on_ui():
                self._webview.evaluateJavascript(js_code, None)

            self._activity.runOnUiThread(run_on_ui)
