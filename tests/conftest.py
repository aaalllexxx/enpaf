"""Shared pytest fixtures for the ENPAF test suite.

The tests exercise the *desktop / dev-mode* behaviour of the framework — the
parts that run without Android/Chaquopy. Anything that needs a real device
(actual sensors, Java callbacks) is covered only at the dispatch/validation
level, since it cannot be imported off-device.
"""

import json
import os

import pytest


MINIMAL_INDEX = (
    "<!DOCTYPE html><html><head><title>{{ title }}</title></head>"
    "<body><h1>{{ title }}</h1></body></html>"
)


@pytest.fixture
def project(tmp_path, monkeypatch):
    """Create an isolated ENPAF project tree and chdir into it.

    Sets ENPAF_DATA_DIR so the SQLite DB lands in the tmp dir (never next to
    the real project) and guarantees dev-mode (ENPAF_ANDROID unset).
    """
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "index.html").write_text(MINIMAL_INDEX, encoding="utf-8")
    (tmp_path / "enpaf.json").write_text(
        json.dumps(
            {
                "name": "TestApp",
                "package": "com.enpaf.test",
                "version": "1.2.3",
                "permissions": ["INTERNET"],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("ENPAF_ANDROID", raising=False)
    monkeypatch.setenv("ENPAF_DATA_DIR", str(tmp_path / "_data"))
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def app(project):
    """A fully constructed, dev-mode EnpafApp rooted at the tmp project."""
    from enpaf import EnpafApp

    return EnpafApp("__main__")


@pytest.fixture
def storage(tmp_path):
    """A standalone Storage backed by a tmp SQLite file."""
    from enpaf.core.storage import Storage

    s = Storage(str(tmp_path / "store.db"))
    yield s
    s.close()


@pytest.fixture
def device_api():
    """A dev-mode DeviceAPI (is_android=False)."""
    from enpaf.core.api import DeviceAPI

    return DeviceAPI(is_android=False)
