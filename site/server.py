#!/usr/bin/env python3
"""ENPAF product site — static server + a tiny visitor counter.

Stdlib only (no third-party packages), same spirit as the previous
`python -m http.server`. On top of static file serving it adds one endpoint:

    GET /api/visits          -> {"count": <n>}   and increments the counter
    GET /api/visits?peek=1   -> {"count": <n>}   read-only, no increment

The count is persisted to ``guest.stxt`` (a single integer) next to this file.
Writes are serialised with a lock and done atomically (temp file + os.replace),
so concurrent requests can't corrupt or lose a count.
"""

from __future__ import annotations

import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
COUNTER_FILE = os.path.join(HERE, "guest.stxt")

_lock = threading.Lock()


def _read_count() -> int:
    try:
        with open(COUNTER_FILE, "r", encoding="utf-8") as fh:
            return int((fh.read() or "0").strip() or "0")
    except (FileNotFoundError, ValueError):
        return 0


def _write_count(value: int) -> None:
    # Atomic replace so a reader never sees a half-written file.
    tmp = COUNTER_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(str(value))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, COUNTER_FILE)


def _bump(increment: bool) -> int:
    with _lock:
        count = _read_count()
        if increment:
            count += 1
            _write_count(count)
        return count


class Handler(SimpleHTTPRequestHandler):
    # Serve files from the site directory regardless of the CWD.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 (stdlib naming)
        parsed = urlparse(self.path)
        if parsed.path == "/api/visits":
            peek = parse_qs(parsed.query).get("peek", ["0"])[0] in ("1", "true", "yes")
            try:
                count = _bump(increment=not peek)
                self._send_json({"count": count})
            except OSError:
                # Never let a counter failure take the page down.
                self._send_json({"count": None, "error": "counter unavailable"}, 200)
            return
        super().do_GET()

    # Quieter logs (skip the default per-request stderr spam).
    def log_message(self, fmt, *args):  # noqa: A003
        pass


def main() -> None:
    host = os.environ.get("ENPAF_SITE_HOST", "0.0.0.0")
    port = int(os.environ.get("ENPAF_SITE_PORT", "5000"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"ENPAF site on http://{host}:{port}  (counter -> {COUNTER_FILE})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
