"""Tests for enpaf.core.api — DeviceAPI dev stubs, dispatcher and helpers."""

import pytest

from enpaf.core.api import DeviceAPI, resolve_permission, _normalize_uri


# ─── Pure helpers ─────────────────────────────────────────────

@pytest.mark.parametrize(
    "name,expected",
    [
        ("CAMERA", "android.permission.CAMERA"),
        ("camera", "android.permission.CAMERA"),
        ("FINE_LOCATION", "android.permission.ACCESS_FINE_LOCATION"),
        ("MICROPHONE", "android.permission.RECORD_AUDIO"),
        ("NFC", "android.permission.NFC"),
        ("android.permission.CUSTOM", "android.permission.CUSTOM"),
        ("SOME_UNKNOWN", "android.permission.SOME_UNKNOWN"),
        ("", ""),
    ],
)
def test_resolve_permission(name, expected):
    assert resolve_permission(name) == expected


@pytest.mark.parametrize(
    "uri,expected",
    [
        ("https://example.com", "https://example.com"),
        ("example.com", "https://example.com"),
        ("tel:+123", "tel:+123"),
        ("mailto:a@b.com", "mailto:a@b.com"),
        ("geo:1,2", "geo:1,2"),
        ("//cdn.example.com", "https://cdn.example.com"),
        ("", ""),
    ],
)
def test_normalize_uri(uri, expected):
    assert _normalize_uri(uri) == expected


# ─── Dev-mode device stubs ────────────────────────────────────

def test_read_sensor_dev_stub(device_api):
    res = device_api.read_sensor("accelerometer")
    assert res["dev"] is True
    assert res["sensor"] == "accelerometer"
    assert isinstance(res["values"], list) and res["values"]


def test_read_unknown_sensor(device_api):
    res = device_api.read_sensor("does_not_exist")
    assert res["available"] is False
    assert "error" in res


def test_list_sensors_dev(device_api):
    res = device_api.list_sensors()
    assert res["dev"] is True
    assert any(s["name"] == "accelerometer" for s in res["sensors"])


def test_get_location_dev(device_api):
    res = device_api.get_location()
    assert res["dev"] is True
    assert "latitude" in res and "longitude" in res


def test_get_battery_dev(device_api):
    res = device_api.get_battery()
    assert res["dev"] is True
    assert "level" in res and "charging" in res


def test_get_network_dev(device_api):
    res = device_api.get_network()
    assert res["dev"] is True
    assert "connected" in res


def test_get_sensor_snapshot_aggregates(device_api):
    snap = device_api.get_sensor_snapshot()
    for key in ("location", "accelerometer", "battery", "network", "nfc"):
        assert key in snap


def test_check_permission_dev_not_granted(device_api):
    res = device_api.check_permission("CAMERA")
    assert res["permission"] == "android.permission.CAMERA"
    assert res["granted"] is False


def test_check_permissions_partition(device_api):
    res = device_api.check_permissions(["CAMERA", "NFC"])
    # Dev mode: nothing granted.
    assert set(res["denied"]) == {"CAMERA", "NFC"}
    assert res["granted"] == []


# ─── Dispatcher ───────────────────────────────────────────────

def test_invoke_dispatches_allowed_method(device_api):
    res = device_api.invoke("get_battery", {})
    assert res["dev"] is True


def test_invoke_passes_kwargs(device_api):
    res = device_api.invoke("read_sensor", {"sensor": "gyroscope"})
    assert res["sensor"] == "gyroscope"


def test_invoke_rejects_unknown_method(device_api):
    with pytest.raises(ValueError):
        device_api.invoke("rm_rf_root", {})


def test_invoke_rejects_private_method(device_api):
    # Only allow-listed methods are reachable, never arbitrary attributes.
    with pytest.raises(ValueError):
        device_api.invoke("set_bridge", {})


def test_allowed_methods_are_all_real_callables():
    api = DeviceAPI(is_android=False)
    for name in DeviceAPI._ALLOWED_METHODS:
        assert callable(getattr(api, name)), name


def test_toast_and_vibrate_are_noops_in_dev(device_api):
    # Should not raise off-device.
    device_api.toast("hi")
    device_api.vibrate(50)
