"""Tests for enpaf.core.app — the EnpafApp facade and its built-in handlers."""

import pytest


def test_config_loaded_from_enpaf_json(app):
    assert app.name == "TestApp"
    assert app.config["package"] == "com.enpaf.test"
    assert app.config["version"] == "1.2.3"


def test_not_android_in_dev(app):
    assert app._detect_android() is False
    assert app.api._is_android is False


def test_route_decorator_registers(app):
    @app.route("/")
    def index():
        return "home"

    assert app.router.resolve("/") is not None


def test_bridge_handler_decorator(app):
    @app.bridge_handler("greet")
    def greet(params):
        return {"hi": params.get("name")}

    res = app.bridge.handle_call("greet", {"name": "Alex"})
    assert res["success"] is True
    assert res["data"] == {"hi": "Alex"}


def test_bridge_func_is_alias(app):
    @app.bridge_func("ping2")
    def ping2(params):
        return "pong"

    assert "ping2" in app.bridge.get_registered_handlers()


def test_on_registers_event_handler(app):
    seen = []

    @app.on("custom")
    def handler(data):
        seen.append(data)

    app.emit("custom", {"v": 1})
    assert seen == [{"v": 1}]


def test_emit_does_not_raise_without_js_target(app):
    app.emit("no_listeners", {"x": 1})


def test_render_injects_app_context(app):
    html = app.render("index.html", title="Hi")
    assert "<title>Hi</title>" in html
    assert "/enpaf-bridge/enpaf.js" in html


# ─── Built-in bridge handlers ─────────────────────────────────

def test_builtin_ping(app):
    res = app.bridge.handle_call("__enpaf_ping", {})
    assert res["data"]["pong"] is True


def test_builtin_storage_roundtrip(app):
    set_res = app.bridge.handle_call("__enpaf_storage_set", {"key": "k", "value": {"a": 1}})
    assert set_res["data"]["success"] is True
    get_res = app.bridge.handle_call("__enpaf_storage_get", {"key": "k"})
    assert get_res["data"]["value"] == {"a": 1}
    del_res = app.bridge.handle_call("__enpaf_storage_delete", {"key": "k"})
    assert del_res["data"]["success"] is True


def test_builtin_get_config(app):
    res = app.bridge.handle_call("__enpaf_get_config", {})
    assert res["data"]["name"] == "TestApp"


def test_builtin_api_gateway(app):
    res = app.bridge.handle_call("__enpaf_api", {"method": "get_battery", "args": {}})
    assert res["success"] is True
    assert res["data"]["dev"] is True


def test_builtin_api_gateway_rejects_unknown(app):
    res = app.bridge.handle_call("__enpaf_api", {"method": "danger", "args": {}})
    assert res["success"] is False


def test_builtin_mod_gateway(app):
    res = app.bridge.handle_call(
        "__enpaf_mod", {"module": "battery", "method": "info", "args": {}}
    )
    assert res["success"] is True
    assert res["data"]["dev"] is True


def test_builtin_mod_gateway_unknown_module(app):
    res = app.bridge.handle_call(
        "__enpaf_mod", {"module": "nope", "method": "x", "args": {}}
    )
    assert res["success"] is False


# ─── Capability modules wired onto the app ────────────────────

EXPECTED_MODULES = [
    "bluetooth", "wifi", "location", "sensors", "nfc", "audio",
    "battery", "notifications", "device", "permissions", "media", "biometric",
]


@pytest.mark.parametrize("name", EXPECTED_MODULES)
def test_module_attached(app, name):
    assert hasattr(app, name)
    assert name in app._modules


def test_storage_db_uses_data_dir(app, project):
    app.storage.set("persisted", 1)
    db_files = list((project / "_data").glob("*.db"))
    assert db_files, "expected the SQLite DB to be created under ENPAF_DATA_DIR"
