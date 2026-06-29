"""Tests for enpaf.android capability managers (dev-mode dispatch).

On-device behaviour needs Chaquopy, but the dispatch layer (invoke /
allow-listing) and the managers that delegate to DeviceAPI dev stubs are fully
testable off-device.
"""

import pytest

from enpaf.android.manager import Manager


# ─── Base Manager dispatch ────────────────────────────────────

class _Demo(Manager):
    NAME = "demo"
    _ALLOWED = {"echo"}

    def echo(self, value=None, **_):
        return {"value": value}


def test_manager_invoke_allowed():
    m = _Demo(app=None)
    assert m.invoke("echo", {"value": 42}) == {"value": 42}


def test_manager_invoke_unknown_raises():
    m = _Demo(app=None)
    with pytest.raises(ValueError):
        m.invoke("nope", {})


def test_manager_invoke_none_args():
    m = _Demo(app=None)
    assert m.invoke("echo") == {"value": None}


# ─── Real managers delegating to DeviceAPI dev stubs ──────────

def test_battery_module_info(app):
    res = app.battery.invoke("info", {})
    assert res["dev"] is True
    assert "level" in res


def test_battery_module_network(app):
    res = app.battery.invoke("network", {})
    assert res["dev"] is True


def test_location_module_get(app):
    res = app.location.invoke("get", {})
    assert "latitude" in res


def test_location_is_available(app):
    res = app.location.invoke("is_available", {})
    assert set(res) >= {"available", "fix"}


def test_device_module_vibrate_returns_ok(app):
    assert app.device.invoke("vibrate", {"milliseconds": 10}) == {"ok": True}


def test_device_module_toast_returns_ok(app):
    assert app.device.invoke("toast", {"message": "hi"}) == {"ok": True}


@pytest.mark.parametrize(
    "module,method",
    [
        ("battery", "bogus"),
        ("location", "bogus"),
        ("device", "bogus"),
        ("wifi", "bogus"),
        ("bluetooth", "bogus"),
    ],
)
def test_unknown_method_rejected_per_module(app, module, method):
    with pytest.raises(ValueError):
        getattr(app, module).invoke(method, {})


def test_every_module_exposes_dispatch_contract(app):
    # Every capability module is reachable via __enpaf_mod, so each must offer
    # an invoke() and a non-empty _ALLOWED allow-list (NAME exists only on the
    # Manager-based ones; bluetooth/wifi are standalone).
    for name, module in app._modules.items():
        assert callable(getattr(module, "invoke", None)), name
        assert isinstance(module._ALLOWED, set)
        assert module._ALLOWED, f"{name} exposes no methods"


def test_allowed_methods_resolve_to_callables(app):
    for name, module in app._modules.items():
        for method in module._ALLOWED:
            assert callable(getattr(module, method)), f"{name}.{method}"
