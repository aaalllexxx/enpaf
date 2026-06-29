"""
ENPAF Core — Main Application Class
The central class that ties together all framework components.
"""

import json
import logging
import os
import sys
from typing import Any, Callable, Dict, List, Optional

from enpaf.core.bridge import Bridge
from enpaf.core.events import EventEmitter
from enpaf.core.router import Router
from enpaf.core.storage import Storage
from enpaf.core.api import DeviceAPI
from enpaf.android.bluetooth import BluetoothManager
from enpaf.android.wifi import WifiManager
from enpaf.android.location import LocationManager
from enpaf.android.sensors import SensorsManager
from enpaf.android.nfc import NfcManager
from enpaf.android.audio import AudioManager
from enpaf.android.battery import BatteryManager
from enpaf.android.notifications import NotificationsManager
from enpaf.android.device import DeviceManager
from enpaf.android.permissions import PermissionsManager
from enpaf.android.media import MediaManager
from enpaf.android.biometric import BiometricManager

logger = logging.getLogger("enpaf")


class EnpafApp:
    """
    Main ENPAF application class.
    
    This is the primary entry point for developers building apps
    with the ENPAF framework.
    
    Usage:
        from enpaf import EnpafApp
        
        app = EnpafApp(__name__)
        
        @app.route("/")
        def index():
            return app.render("index.html", title="My App")
        
        @app.bridge("get_users")
        def get_users(params):
            return [{"name": "Alex", "age": 25}]
        
        @app.on("app_start")
        def on_start():
            print("App started!")
        
        app.run()
    """

    def __init__(self, import_name: str, app_dir: str = "app", config_file: str = "enpaf.json"):
        """
        Initialize the ENPAF application.
        
        Args:
            import_name: The name of the application module (usually __name__)
            app_dir: Directory containing HTML/CSS/JS files (default: "app")
            config_file: Path to the project config file (default: "enpaf.json")
        """
        # Determine project directory
        if import_name == "__main__":
            self._project_dir = os.getcwd()
        else:
            module = sys.modules.get(import_name)
            if module and hasattr(module, "__file__") and module.__file__:
                self._project_dir = os.path.dirname(os.path.abspath(module.__file__))
            else:
                self._project_dir = os.getcwd()

        self._app_dir = os.path.join(self._project_dir, app_dir)
        self._config_file = os.path.join(self._project_dir, config_file)
        self._config: Dict[str, Any] = {}
        self._is_android = self._detect_android()

        # Initialize components
        self.bridge = Bridge()
        self.events = EventEmitter()
        self.router = Router(self._app_dir)
        self.storage = Storage(self._resolve_data_path("enpaf_data.db"))
        self.api = DeviceAPI(is_android=self._is_android)

        # Connect API to bridge
        self.api.set_bridge(self.bridge)

        # Capability modules — reachable as app.<name> and from JS as
        # enpaf.<name>.* (dispatched through the __enpaf_mod bridge handler).
        self.bluetooth = BluetoothManager(self)
        self.wifi = WifiManager(self)
        self.location = LocationManager(self)
        self.sensors = SensorsManager(self)
        self.nfc = NfcManager(self)
        self.audio = AudioManager(self)
        self.battery = BatteryManager(self)
        self.notifications = NotificationsManager(self)
        self.device = DeviceManager(self)
        self.permissions = PermissionsManager(self)
        self.media = MediaManager(self)
        self.biometric = BiometricManager(self)

        self._modules = {
            "bluetooth": self.bluetooth, "wifi": self.wifi, "location": self.location,
            "sensors": self.sensors, "nfc": self.nfc, "audio": self.audio,
            "battery": self.battery, "notifications": self.notifications,
            "device": self.device, "permissions": self.permissions,
            "media": self.media, "biometric": self.biometric,
        }

        # Load config
        self._load_config()

        # Register built-in bridge handlers
        self._register_builtins()

        # Setup logging
        self._setup_logging()

    def _detect_android(self) -> bool:
        """Detect if running on Android.

        MainActivity sets ENPAF_ANDROID=1 before importing the app. We rely on
        that rather than `import android`, which Chaquopy does not provide.
        """
        if os.environ.get("ENPAF_ANDROID") == "1":
            return True
        # Chaquopy resolves Java *classes* (from android.os import Build), but a
        # bare `import android` can raise ModuleNotFoundError even on-device, so
        # never let this detection crash the app — fall back to "not Android".
        try:
            from com.chaquo.python import Python  # noqa: F401
            return True
        except Exception:
            pass
        try:
            import android  # noqa: F401
            return True
        except Exception:
            return False

    def _resolve_data_path(self, filename: str) -> str:
        """Return a writable path for app data.

        On Android the project directory lives in a read-only asset location,
        so MainActivity passes the app's files dir via ENPAF_DATA_DIR. Writing
        the SQLite DB there (instead of next to the source) is what prevents the
        immediate crash-on-launch.
        """
        data_dir = os.environ.get("ENPAF_DATA_DIR")
        if not data_dir:
            data_dir = os.path.join(self._project_dir, "data")
        try:
            os.makedirs(data_dir, exist_ok=True)
        except OSError:
            pass
        return os.path.join(data_dir, filename)

    def _load_config(self):
        """Load project configuration from enpaf.json."""
        if os.path.isfile(self._config_file):
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                logger.debug(f"Config loaded: {self._config.get('name', 'unnamed')}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load config: {e}")
        else:
            logger.debug("No enpaf.json found, using defaults")

    def _setup_logging(self):
        """Configure logging for the framework."""
        log_level = self._config.get("log_level", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format="%(asctime)s  %(message)s",
            datefmt="%H:%M:%S",
        )

    def _register_builtins(self):
        """Register built-in bridge handlers."""

        @self.bridge.register("__enpaf_ping")
        def ping(params):
            return {"pong": True, "version": "1.0.0"}

        @self.bridge.register("__enpaf_storage_get")
        def storage_get(params):
            key = params.get("key", "")
            return {"value": self.storage.get(key)}

        @self.bridge.register("__enpaf_storage_set")
        def storage_set(params):
            key = params.get("key", "")
            value = params.get("value")
            self.storage.set(key, value)
            return {"success": True}

        @self.bridge.register("__enpaf_storage_delete")
        def storage_delete(params):
            key = params.get("key", "")
            return {"success": self.storage.delete(key)}

        @self.bridge.register("__enpaf_get_config")
        def get_config(params):
            return self._config

        @self.bridge.register("__enpaf_api")
        def api_call(params):
            """Generic gateway to DeviceAPI (sensors, permissions, device features).

            JS: enpaf.call("__enpaf_api", { method: "get_location", args: {} })
            """
            method = params.get("method", "")
            args = params.get("args", {}) or {}
            return self.api.invoke(method, args)

        @self.bridge.register("__enpaf_mod")
        def mod_call(params):
            """Gateway to a capability module (wifi, bluetooth, sensors, ...).

            JS: enpaf.mod("wifi", "scan", {})  ->  app.wifi.scan()
            """
            name = params.get("module", "")
            module = self._modules.get(name)
            if module is None:
                raise ValueError(f"unknown module: {name!r}")
            return module.invoke(params.get("method", ""), params.get("args", {}) or {})

    # --- Android wiring (called from MainActivity via Python) ---

    def _attach_android(self, activity, webview=None):
        """Receive the Activity (+ WebView) from Java.

        Enables on-demand permission requests (need an Activity) and lets Python
        push events into the WebView (Python -> JS) without SocketIO.
        """
        self.api.set_activity(activity)
        if webview is not None:
            self.bridge.set_android_webview(activity, webview)
        # enpaf.json isn't readable from the APK's asset path at runtime, so
        # fill in the real package/name from the Activity (used by AAR records,
        # app.name, etc.).
        try:
            if not self._config.get("package"):
                self._config["package"] = str(activity.getPackageName())
            if not self._config.get("name"):
                pm = activity.getPackageManager()
                self._config["name"] = str(pm.getApplicationLabel(activity.getApplicationInfo()))
        except Exception as e:
            logger.debug(f"Could not read package info from Activity: {e}")
        logger.debug("Android Activity attached to ENPAF app")

    def _on_permission_result(self, code, permissions, grant_results):
        """Called from MainActivity.onRequestPermissionsResult.

        Normalizes the Java arrays and fans the result out to JS (the
        `permission_result` event) and Python event handlers.
        """
        try:
            perms = [str(p) for p in permissions]
            grants = [int(g) for g in grant_results]
        except Exception:
            perms, grants = [], []
        results = {p: (g == 0) for p, g in zip(perms, grants)}
        payload = {
            "code": int(code),
            "results": results,
            "granted": [p for p, ok in results.items() if ok],
            "denied": [p for p, ok in results.items() if not ok],
        }
        self.events.emit("permission_result", payload)
        self.bridge.emit_to_js("permission_result", payload)

    def _on_install_status(self, status, message=""):
        """Called from MainActivity with a PackageInstaller final status
        (success/failure). STATUS_SUCCESS == 0."""
        payload = {"status": int(status), "success": int(status) == 0, "message": str(message or "")}
        self.events.emit("install_status", payload)
        self.bridge.emit_to_js("install_status", payload)

    def _on_biometric_result(self, success, error=""):
        """Called from MainActivity after the biometric prompt resolves."""
        payload = {"success": bool(success), "error": str(error or "")}
        self.events.emit("biometric_result", payload)
        self.bridge.emit_to_js("biometric_result", payload)

    def _on_activity_result(self, request_code, result_code, data):
        """Called from MainActivity.onActivityResult."""
        import logging
        logging.getLogger("enpaf").debug(
            f"activity_result code={request_code} result={result_code} data={data}")
        payload = {
            "request_code": int(request_code),
            "result_code": int(result_code),
            "data": data,
        }
        self.events.emit("activity_result", payload)

    def _on_broadcast_receive(self, tag, intent):
        """Called from MainActivity.EnpafBroadcastReceiver.onReceive.

        The `tag` is a string identifier set when registerEnpafReceiver was called.
        Emits `broadcast:<tag>` so only the right module picks it up.
        """
        import logging
        logging.getLogger("enpaf").debug(f"broadcast_receive tag={tag} action={intent.getAction()}")
        self.events.emit(f"broadcast:{tag}", {"intent": intent})

    def _on_nfc_tag(self, tag_id, from_launch=False):
        """Called from MainActivity (UI thread) when an NFC tag is scanned.

        Emits the `nfc_tag` event immediately, then does all tag I/O on a
        background thread — NFC connect/read/write must not run on the main
        thread (it can ANR or throw).
        """
        tag_id = str(tag_id)
        from_launch = bool(from_launch)
        payload = {"id": tag_id, "from_launch": from_launch}
        self.events.emit("nfc_tag", payload)
        self.bridge.emit_to_js("nfc_tag", payload)

        import threading
        threading.Thread(target=self._process_nfc_tag,
                         args=(tag_id, from_launch), daemon=True).start()

    def _process_nfc_tag(self, tag_id, from_launch):
        """Off-thread: run an armed write, or auto-open a URL on launch."""
        # If a write/lock was armed (enpaf.nfc.arm*), run it while the tag
        # handle is still valid, and report the outcome.
        try:
            result = self.api.consume_pending_nfc()
        except Exception as e:
            result = {"written": False, "error": str(e)}
        if result is not None:
            result = {**result, "id": tag_id}
            self.events.emit("nfc_write_result", result)
            self.bridge.emit_to_js("nfc_write_result", result)
            return

        # Tag launched the app: open the first URL it carries (deterministic
        # "tap -> open link" that does not depend on the OS tag dispatcher).
        if from_launch:
            try:
                data = self.api.nfc_read()
                for rec in (data.get("records") or []):
                    if rec.get("type") == "uri" and rec.get("uri"):
                        self.api.open_url(rec["uri"])
                        self.bridge.emit_to_js("nfc_open", {"uri": rec["uri"]})
                        break
            except Exception as e:
                logger.error(f"nfc launch-open error: {e}")

    # --- Public API (Decorators) ---

    def route(self, path: str, methods: List[str] = None) -> Callable:
        """
        Register a page route.
        
            @app.route("/")
            def index():
                return app.render("index.html")
        """
        return self.router.route(path, methods)

    def bridge_handler(self, name: str) -> Callable:
        """
        Register a bridge handler callable from JavaScript.
        
            @app.bridge_handler("get_data")
            def get_data(params):
                return {"users": [...]}
        
        In JavaScript: const data = await enpaf.call("get_data", {page: 1});
        """
        return self.bridge.register(name)

    # Alias for convenience
    def bridge_func(self, name: str) -> Callable:
        """Alias for bridge_handler()."""
        return self.bridge_handler(name)

    def on(self, event: str) -> Callable:
        """
        Register an event handler (decorator).
        
            @app.on("app_start")
            def on_start():
                print("Started!")
        """
        def decorator(handler: Callable) -> Callable:
            self.events.on(event, handler)
            return handler
        return decorator

    def emit(self, event: str, data: Any = None) -> None:
        """
        Emit an event to both Python handlers and JavaScript.
        
            app.emit("data_updated", {"count": 42})
        """
        self.events.emit(event, data)
        self.bridge.emit_to_js(event, data)

    def render(self, template_name: str, **context) -> str:
        """
        Render an HTML template.
        
            return app.render("index.html", title="Home", users=users)
        """
        # Add app config to context
        context.setdefault("config", self._config)
        context.setdefault("app_name", self._config.get("name", "ENPAF App"))
        return self.router.render(template_name, **context)

    @property
    def config(self) -> Dict[str, Any]:
        """Get the project configuration."""
        return self._config

    @property
    def name(self) -> str:
        """Get the app name."""
        return self._config.get("name", "ENPAF App")

    # --- Run ---

    def run(self, host: str = "127.0.0.1", port: int = 8080,
            debug: bool = False, open_browser: bool = True):
        """
        Start the application.
        
        In dev mode, starts the Flask development server.
        On Android, initializes the WebView runtime.
        
        Args:
            host: Server host (default: 127.0.0.1)
            port: Server port (default: 8080)
            debug: Enable debug mode
            open_browser: Auto-open browser on start
        """
        if self._detect_android():
            self._run_android()
        else:
            self._run_dev(host, port, debug, open_browser)

    def _run_dev(self, host: str, port: int, debug: bool, open_browser: bool):
        """Start the development server."""
        from enpaf.core.server import DevServer

        lines = [
            "",
            "  +-----------------------------------------------+",
            f"  |  ENPAF Dev Server - {self.name:<26.26s}|",
            "  +-----------------------------------------------+",
            "",
            f"  App:       http://{host}:{port}",
            f"  Settings:  http://{host}:{port}/enpaf-settings",
            f"  App dir:   {self._app_dir}",
            f"  Handlers:  {len(self.bridge.get_registered_handlers())}",
            "",
            "  Press Ctrl+C to stop",
            "",
        ]
        # Some Windows consoles default to a legacy code page (cp1251 etc.) that
        # cannot encode every character; never let the banner crash startup.
        for line in lines:
            try:
                print(line)
            except UnicodeEncodeError:
                print(line.encode("ascii", "replace").decode("ascii"))

        server = DevServer(self, host, port)
        server.run(debug=debug, open_browser=open_browser)

    def _run_android(self):
        """Start the Android runtime."""
        try:
            from enpaf.android.runtime import AndroidRuntime
            runtime = AndroidRuntime(self)
            runtime.start()
        except ImportError:
            logger.error("Android runtime not available in this environment")
            raise RuntimeError("Cannot run Android runtime outside of Android")
