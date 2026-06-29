"""Tests for enpaf.core.events — the pub/sub EventEmitter."""

import pytest

from enpaf.core.events import EventEmitter


@pytest.fixture
def emitter():
    return EventEmitter()


def test_on_and_emit_calls_handler(emitter):
    seen = []
    emitter.on("ping", lambda data: seen.append(data))
    emitter.emit("ping", {"x": 1})
    assert seen == [{"x": 1}]


def test_emit_returns_handler_results(emitter):
    emitter.on("calc", lambda n: n * 2)
    emitter.on("calc", lambda n: n + 1)
    assert emitter.emit("calc", 10) == [20, 11]


def test_multiple_handlers_all_fire(emitter):
    calls = []
    emitter.on("e", lambda *_: calls.append("a"))
    emitter.on("e", lambda *_: calls.append("b"))
    emitter.emit("e")
    assert calls == ["a", "b"]


def test_once_fires_only_once(emitter):
    count = []
    emitter.once("boot", lambda *_: count.append(1))
    emitter.emit("boot")
    emitter.emit("boot")
    assert count == [1]


def test_off_removes_specific_handler(emitter):
    calls = []
    h = lambda *_: calls.append(1)
    emitter.on("e", h)
    emitter.off("e", h)
    emitter.emit("e")
    assert calls == []


def test_off_without_handler_clears_all(emitter):
    calls = []
    emitter.on("e", lambda *_: calls.append(1))
    emitter.on("e", lambda *_: calls.append(2))
    emitter.off("e")
    emitter.emit("e")
    assert calls == []


def test_has_listeners_and_count(emitter):
    assert emitter.has_listeners("e") is False
    assert emitter.listener_count("e") == 0
    emitter.on("e", lambda *_: None)
    emitter.once("e", lambda *_: None)
    assert emitter.has_listeners("e") is True
    assert emitter.listener_count("e") == 2


def test_event_names_lists_active_events(emitter):
    emitter.on("a", lambda *_: None)
    emitter.on("b", lambda *_: None)
    assert set(emitter.event_names()) == {"a", "b"}


def test_handler_exception_emits_app_error(emitter):
    errors = []
    emitter.on("app_error", lambda exc, *rest: errors.append(exc))

    def boom(_):
        raise ValueError("nope")

    emitter.on("explode", boom)
    results = emitter.emit("explode", 1)
    assert results == [None]  # failed handler contributes None
    assert len(errors) == 1
    assert isinstance(errors[0], ValueError)


def test_app_error_handler_failure_does_not_recurse(emitter):
    # A failing app_error handler must not trigger infinite recursion.
    emitter.on("app_error", lambda *_: (_ for _ in ()).throw(RuntimeError("bad")))
    emitter.on("x", lambda *_: (_ for _ in ()).throw(ValueError("first")))
    emitter.emit("x")  # should simply return without hanging / overflowing


def test_emit_with_args_and_kwargs(emitter):
    seen = []
    emitter.on("e", lambda *a, **k: seen.append((a, k)))
    emitter.emit("e", 1, 2, key="v")
    assert seen == [((1, 2), {"key": "v"})]


def test_lifecycle_events_constant_present():
    assert "app_start" in EventEmitter.LIFECYCLE_EVENTS
    assert "app_stop" in EventEmitter.LIFECYCLE_EVENTS
