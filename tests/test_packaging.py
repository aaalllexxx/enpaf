"""Sanity checks on packaging metadata and the public import surface."""

import pathlib
import re

import enpaf

ROOT = pathlib.Path(__file__).resolve().parent.parent
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def _project_version():
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', PYPROJECT)
    assert m, "version not found in pyproject.toml"
    return m.group(1)


def test_version_matches_pyproject():
    assert enpaf.__version__ == _project_version()


def test_public_api_exports_app():
    assert hasattr(enpaf, "EnpafApp")
    assert "EnpafApp" in enpaf.__all__


def test_paf_entry_point_declared():
    assert 'paf = "enpaf.cli.main:main"' in PYPROJECT


def test_entry_point_callable_is_importable():
    from enpaf.cli.main import main

    assert callable(main)


def test_packages_listed_for_distribution():
    assert "enpaf*" in PYPROJECT
    assert "enpaf_bridge*" in PYPROJECT
