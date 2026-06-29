"""Tests for enpaf.core.bridge — the Python <-> JS bridge."""

import pytest

from enpaf.core.bridge import Bridge


@pytest.fixture
def bridge():
    return Bridge()


def test_register_as_decorator(bridge):
    @bridge.register("hello")
    def hello(params):
        return {"msg": "hi"}

    assert "hello" in bridge.get_registered_handlers()


def test_register_directly(bridge):
    bridge.register("add", lambda p: p["a"] + p["b"])
    res = bridge.handle_call("add", {"a": 2, "b": 3})
    assert res["success"] is True
    assert res["data"] == 5


def test_handle_call_success_envelope(bridge):
    bridge.register("echo", lambda p: p)
    res = bridge.handle_call("echo", {"x": 1}, call_id="c1")
    assert res == {"success": True, "data": {"x": 1}, "callId": "c1"}


def test_handle_call_unknown_handler(bridge):
    res = bridge.handle_call("missing", {})
    assert res["success"] is False
    assert "not found" in res["error"]


def test_handle_call_handler_exception_is_caught(bridge):
    @bridge.register("boom")
    def boom(_):
        raise RuntimeError("kaboom")

    res = bridge.handle_call("boom", {})
    assert res["success"] is False
    assert "kaboom" in res["error"]


def test_handle_call_defaults_params_to_empty(bridge):
    bridge.register("noargs", lambda p: {"keys": list(p.keys())})
    res = bridge.handle_call("noargs")
    assert res["success"] is True
    assert res["data"] == {"keys": []}


def test_unregister(bridge):
    bridge.register("temp", lambda p: 1)
    bridge.unregister("temp")
    assert "temp" not in bridge.get_registered_handlers()


def test_emit_to_js_uses_socketio_when_present(bridge):
    emitted = []

    class FakeSocketIO:
        def emit(self, channel, payload):
            emitted.append((channel, payload))

    bridge.set_socketio(FakeSocketIO())
    bridge.emit_to_js("data_updated", {"count": 7})
    assert emitted == [("enpaf_event", {"event": "data_updated", "data": {"count": 7}})]


def test_emit_to_js_without_target_is_noop(bridge):
    # No socketio, no android webview — should not raise.
    bridge.emit_to_js("event", {"a": 1})


def test_js_event_handlers(bridge):
    received = []
    bridge.on_js_event("clicked", lambda data: received.append(data))
    bridge.handle_js_event("clicked", {"id": "save"})
    assert received == [{"id": "save"}]


def test_js_event_handler_exception_isolated(bridge):
    received = []

    def bad(_):
        raise ValueError("x")

    bridge.on_js_event("e", bad)
    bridge.on_js_event("e", lambda d: received.append(d))
    bridge.handle_js_event("e", 1)  # bad handler must not stop the good one
    assert received == [1]
