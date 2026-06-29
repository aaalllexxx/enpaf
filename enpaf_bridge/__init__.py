"""ENPAF JavaScript bridge assets.

Ships the client-side `enpaf.js` SDK that the dev server serves and the APK
builder copies into the app's WebView assets.
"""

import os

__all__ = ["bridge_js_path", "bridge_dir", "socketio_js_path"]


def bridge_dir() -> str:
    """Absolute path to the directory containing enpaf.js."""
    return os.path.dirname(os.path.abspath(__file__))


def bridge_js_path() -> str:
    """Absolute path to the bundled enpaf.js bridge file."""
    return os.path.join(bridge_dir(), "enpaf.js")


def socketio_js_path() -> str:
    """Absolute path to the bundled Socket.IO browser client.

    Bundled so the dev server never depends on the CDN (works offline) and so
    the page never tries to execute Engine.IO's HTTP 400 body as a script.
    """
    return os.path.join(bridge_dir(), "socket.io.min.js")
