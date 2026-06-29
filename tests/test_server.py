"""Tests for enpaf.core.server — the dev server wiring + hardening.

Covers the Socket.IO CORS policy and the static-file routing (incl. the
path-traversal guard) via Flask's test client. No real server is started.
"""

import pytest

from enpaf.core.server import DevServer


# ─── CORS origin policy ───────────────────────────────────────

def test_cors_loopback_is_same_origin_allowlist():
    origins = DevServer._cors_origins("127.0.0.1", 8080)
    assert origins == ["http://localhost:8080", "http://127.0.0.1:8080"]


def test_cors_localhost_is_same_origin_allowlist():
    assert "http://localhost:3000" in DevServer._cors_origins("localhost", 3000)


def test_cors_non_loopback_is_open():
    # Explicit external bind opts into open CORS (with a warning at runtime).
    assert DevServer._cors_origins("0.0.0.0", 8080) == "*"
    assert DevServer._cors_origins("192.168.0.10", 8080) == "*"


# ─── Static serving + traversal guard ─────────────────────────

@pytest.fixture
def client(app):
    server = DevServer(app, host="127.0.0.1", port=8080)
    flask_app = server.create_flask_app()
    flask_app.config.update(TESTING=True)
    return flask_app.test_client()


def test_serves_index_with_bridge_injected(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "/enpaf-bridge/enpaf.js" in body  # bridge auto-injected


def test_handlers_endpoint(client):
    r = client.get("/enpaf-api/handlers")
    assert r.status_code == 200
    assert "handlers" in r.get_json()


def test_http_bridge_call_fallback(client):
    r = client.post("/enpaf-api/bridge-call", json={"name": "__enpaf_ping", "params": {}})
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["data"]["pong"] is True


def test_http_bridge_call_missing_name(client):
    r = client.post("/enpaf-api/bridge-call", json={"params": {}})
    assert r.status_code == 400


def test_bridge_assets_allowlist(client):
    assert client.get("/enpaf-bridge/enpaf.js").status_code == 200
    # Anything not on the allow-list is refused.
    assert client.get("/enpaf-bridge/secrets.js").status_code == 404


def test_path_traversal_is_blocked(client):
    # A crafted absolute-ish traversal must not escape the app dir.
    r = client.get("/..%2f..%2f..%2fetc%2fpasswd")
    assert r.status_code in (403, 404)  # never 200 with file contents
