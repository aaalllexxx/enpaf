"""
ENPAF Core — Development Server
Flask-based dev server with WebSocket bridge, hot-reload, and static file serving.
"""

import logging
import os
import sys
import threading
import time
import mimetypes
from typing import Optional

from flask import Flask, send_from_directory, request, jsonify, Response
from flask_socketio import SocketIO

from enpaf.core import config_panel

logger = logging.getLogger("enpaf.server")


class DevServer:
    """
    Development server for ENPAF apps.
    
    Features:
    - Serves HTML/CSS/JS from the app directory
    - WebSocket bridge for Python ↔ JS communication
    - Auto-injects enpaf.js bridge script
    - File watching with hot-reload
    """

    def __init__(self, app_instance, host: str = "127.0.0.1", port: int = 8080):
        """
        Args:
            app_instance: The EnpafApp instance
            host: Server host
            port: Server port
        """
        self.app_instance = app_instance
        self.host = host
        self.port = port
        self.flask_app: Optional[Flask] = None
        self.socketio: Optional[SocketIO] = None
        self._watcher_thread: Optional[threading.Thread] = None
        self._running = False

    def create_flask_app(self) -> Flask:
        """Create and configure the Flask application."""
        flask_app = Flask(
            __name__,
            static_folder=None,  # We handle static files ourselves
        )
        flask_app.config["SECRET_KEY"] = "enpaf-dev-secret"

        # Initialize SocketIO
        self.socketio = SocketIO(
            flask_app,
            cors_allowed_origins="*",
            async_mode="threading",
            logger=False,
            engineio_logger=False,
        )

        # Connect bridge to SocketIO
        self.app_instance.bridge.set_socketio(self.socketio)

        # Register SocketIO handlers
        self._register_socketio_handlers()

        # Register Flask routes
        self._register_routes(flask_app)

        self.flask_app = flask_app
        return flask_app

    def _register_socketio_handlers(self):
        """Register WebSocket event handlers for the bridge."""

        @self.socketio.on("connect")
        def on_connect():
            logger.info("🔌 Browser connected via WebSocket")
            self.app_instance.events.emit("bridge_connect")

        @self.socketio.on("disconnect")
        def on_disconnect():
            logger.info("🔌 Browser disconnected")
            self.app_instance.events.emit("bridge_disconnect")

        @self.socketio.on("enpaf_call")
        def on_bridge_call(data):
            """Handle a Python function call from JavaScript."""
            name = data.get("name", "")
            params = data.get("params", {})
            call_id = data.get("callId", "")

            logger.debug(f"📨 Bridge call: {name}({params})")
            response = self.app_instance.bridge.handle_call(name, params, call_id)
            return response

        @self.socketio.on("enpaf_event")
        def on_bridge_event(data):
            """Handle an event from JavaScript."""
            event = data.get("event", "")
            payload = data.get("data")
            self.app_instance.bridge.handle_js_event(event, payload)
            self.app_instance.events.emit(event, payload)

    def _register_routes(self, flask_app: Flask):
        """Register HTTP routes."""

        @flask_app.route("/enpaf-bridge/<path:filename>")
        def serve_bridge_js(filename):
            """Serve ENPAF bridge assets (enpaf.js, bundled socket.io client)."""
            if filename not in ("enpaf.js", "socket.io.min.js"):
                return ("", 404)
            try:
                from enpaf_bridge import bridge_dir as _bridge_dir
                directory = _bridge_dir()
            except Exception:
                directory = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    "enpaf_bridge",
                )
            resp = send_from_directory(directory, filename, mimetype="application/javascript")
            # Never let the browser cache the bridge in dev — otherwise newly
            # added APIs (enpaf.wifi, enpaf.bluetooth, …) won't load without a
            # hard refresh.
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return resp

        @flask_app.route("/enpaf-api/handlers")
        def list_handlers():
            """List all registered bridge handlers (for debugging)."""
            return jsonify({
                "handlers": self.app_instance.bridge.get_registered_handlers(),
                "routes": self.app_instance.router.get_routes(),
            })

        @flask_app.route("/enpaf-api/bridge-call", methods=["POST"])
        def http_bridge_call():
            """HTTP fallback for bridge calls when Socket.IO is unavailable.

            Returns the same {success, data/error, callId} envelope that the
            Socket.IO path returns, so enpaf.js can treat both identically.
            """
            data = request.get_json(silent=True) or {}
            name = data.get("name")
            params = data.get("params", {})
            call_id = data.get("callId")
            if not name:
                return jsonify({"success": False, "error": "missing handler name",
                                "callId": call_id}), 400
            try:
                return jsonify(self.app_instance.bridge.handle_call(name, params, call_id))
            except Exception as e:
                import traceback
                traceback.print_exc()
                return jsonify({"success": False, "error": str(e), "callId": call_id}), 500

        @flask_app.route("/enpaf-api/storage/<key>", methods=["GET", "PUT", "DELETE"])
        def storage_api(key):
            """REST API for storage operations."""
            if request.method == "GET":
                value = self.app_instance.storage.get(key)
                return jsonify({"key": key, "value": value})
            elif request.method == "PUT":
                data = request.get_json()
                self.app_instance.storage.set(key, data.get("value"))
                return jsonify({"success": True})
            elif request.method == "DELETE":
                self.app_instance.storage.delete(key)
                return jsonify({"success": True})

        # ─── Settings panel (deep links, permissions, features, icon) ──
        @flask_app.route("/enpaf-settings")
        def enpaf_settings_page():
            return Response(config_panel.render_page(), mimetype="text/html")

        @flask_app.route("/enpaf-api/config", methods=["GET", "POST"])
        def enpaf_config():
            project_dir = self.app_instance._project_dir
            if request.method == "GET":
                return jsonify(config_panel.build_state(project_dir))
            data = request.get_json(silent=True) or {}
            try:
                config = config_panel.save_config(project_dir, data)
            except (ValueError, FileNotFoundError) as e:
                return jsonify({"success": False, "error": str(e)}), 400
            # Reflect the change in the running app immediately.
            self.app_instance._config = config
            return jsonify({
                "success": True,
                "config": config,
                "preview": config_panel.build_preview(
                    config.get("permissions", []),
                    config.get("deeplinks", []),
                    config.get("features", []),
                ),
            })

        @flask_app.route("/enpaf-api/config/preview", methods=["POST"])
        def enpaf_config_preview():
            data = request.get_json(silent=True) or {}
            return jsonify(config_panel.build_preview(
                data.get("permissions", []),
                data.get("deeplinks", []),
                data.get("features", []),
            ))

        @flask_app.route("/enpaf-api/icon", methods=["GET", "POST"])
        def enpaf_icon():
            project_dir = self.app_instance._project_dir
            if request.method == "GET":
                icon = (self.app_instance._config or {}).get("icon")
                if not icon:
                    config = config_panel.load_config(project_dir)
                    icon = config.get("icon")
                if icon and os.path.isfile(os.path.join(project_dir, icon)):
                    return send_from_directory(project_dir, icon)
                return ("", 404)
            f = request.files.get("icon")
            if not f:
                return jsonify({"success": False, "error": "no file uploaded"}), 400
            try:
                rel = config_panel.save_icon(project_dir, f.filename, f.read())
            except ValueError as e:
                return jsonify({"success": False, "error": str(e)}), 400
            return jsonify({"success": True, "icon": rel})

        @flask_app.route("/", defaults={"path": ""})
        @flask_app.route("/<path:path>")
        def serve_app(path):
            """Serve application files with bridge injection."""
            app_dir = self.app_instance._app_dir

            # Check if this is a registered route
            route_result = self.app_instance.router.resolve("/" + path if path else "/")
            if route_result:
                _, handler = route_result
                content = handler()
                return self._inject_bridge(content)

            # Default to index.html for root
            if not path or path == "/":
                path = "index.html"

            # Serve static files
            file_path = os.path.join(app_dir, path)
            if os.path.isfile(file_path):
                # For HTML files, inject bridge
                if path.endswith(".html"):
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    return self._inject_bridge(content)
                else:
                    directory = os.path.dirname(file_path)
                    filename = os.path.basename(file_path)
                    mime_type, _ = mimetypes.guess_type(filename)
                    return send_from_directory(
                        directory, filename, mimetype=mime_type
                    )

            # Try index.html for SPA routing
            index_path = os.path.join(app_dir, "index.html")
            if os.path.isfile(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return self._inject_bridge(content)

            return "404 — Page not found", 404

    def _inject_bridge(self, html_content: str) -> str:
        """Inject the ENPAF bridge script and hot-reload into HTML."""
        bridge_script = """
    <!-- ENPAF Bridge (auto-injected in dev mode) -->
    <script src="/enpaf-bridge/socket.io.min.js"></script>
    <script src="/enpaf-bridge/enpaf.js"></script>
    <a href="/enpaf-settings" target="_blank" id="__enpaf_gear"
       title="ENPAF settings — icon, name, permissions, deep links, features"
       style="position:fixed;bottom:16px;right:16px;z-index:2147483647;width:44px;height:44px;
       border-radius:50%;background:#6C5CE7;color:#fff;display:flex;align-items:center;
       justify-content:center;font-size:20px;text-decoration:none;
       box-shadow:0 4px 12px rgba(0,0,0,.3);opacity:.55;transition:opacity .2s"
       onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=.55">&#9881;</a>
    <script>
        // Hot-reload support
        if (typeof io !== 'undefined') {
            const _enpafSocket = io();
            _enpafSocket.on('enpaf_reload', () => {
                console.log('🔄 ENPAF: Reloading...');
                location.reload();
            });
        }
    </script>
"""
        if "</head>" in html_content:
            return html_content.replace("</head>", bridge_script + "</head>")
        elif "<body" in html_content:
            return bridge_script + html_content
        else:
            return bridge_script + html_content

    def _start_file_watcher(self):
        """Start watching files for changes (hot-reload)."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class ReloadHandler(FileSystemEventHandler):
                def __init__(self, server):
                    self.server = server
                    self._last_reload = 0

                def on_modified(self, event):
                    if event.is_directory:
                        return
                    # Debounce: ignore events within 1 second
                    now = time.time()
                    if now - self._last_reload < 1:
                        return
                    self._last_reload = now

                    ext = os.path.splitext(event.src_path)[1].lower()
                    if ext in (".html", ".css", ".js", ".py"):
                        logger.info(f"🔄 File changed: {os.path.basename(event.src_path)}")
                        if self.server.socketio:
                            self.server.socketio.emit("enpaf_reload")

            observer = Observer()
            app_dir = self.app_instance._app_dir
            if os.path.isdir(app_dir):
                observer.schedule(ReloadHandler(self), app_dir, recursive=True)

            # Also watch main.py
            project_dir = self.app_instance._project_dir
            if os.path.isdir(project_dir):
                observer.schedule(ReloadHandler(self), project_dir, recursive=False)

            observer.start()
            logger.info("👁️  File watcher started (hot-reload enabled)")
            return observer

        except ImportError:
            logger.warning("⚠️  watchdog not installed — hot-reload disabled")
            return None

    def run(self, debug: bool = False, open_browser: bool = True):
        """Start the development server."""
        if self.flask_app is None:
            self.create_flask_app()

        self._running = True

        # Start file watcher
        observer = self._start_file_watcher()

        # Emit app_start event
        self.app_instance.events.emit("app_start")

        # Open browser
        if open_browser:
            def _open():
                time.sleep(1.0)
                import webbrowser
                url = f"http://{self.host}:{self.port}"
                webbrowser.open(url)
            threading.Thread(target=_open, daemon=True).start()

        try:
            self.socketio.run(
                self.flask_app,
                host=self.host,
                port=self.port,
                debug=debug,
                use_reloader=False,  # We handle reloading ourselves
                allow_unsafe_werkzeug=True,
            )
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            self.app_instance.events.emit("app_stop")
            if observer:
                observer.stop()
                observer.join()
