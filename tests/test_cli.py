"""Tests for the `paf` CLI — argument parsing and the create command."""

import json
import sys
from types import SimpleNamespace

import pytest

from enpaf.cli.commands.create import cmd_create
from enpaf.cli.main import main


# ─── create command ───────────────────────────────────────────

def test_create_scaffolds_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cmd_create(SimpleNamespace(name="mynewapp", package=None, template="default"))

    proj = tmp_path / "mynewapp"
    assert (proj / "enpaf.json").is_file()
    assert (proj / "main.py").is_file()
    assert (proj / "app" / "index.html").is_file()

    cfg = json.loads((proj / "enpaf.json").read_text(encoding="utf-8"))
    assert cfg["name"] == "mynewapp"
    assert cfg["package"] == "com.enpaf.mynewapp"


def test_create_uses_custom_package(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cmd_create(SimpleNamespace(name="branded", package="io.acme.app", template="default"))
    cfg = json.loads((tmp_path / "branded" / "enpaf.json").read_text(encoding="utf-8"))
    assert cfg["package"] == "io.acme.app"


def test_create_rejects_invalid_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cmd_create(SimpleNamespace(name="123 bad!", package=None, template="default"))
    assert not (tmp_path / "123 bad!").exists()


def test_create_refuses_existing_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "dupe").mkdir()
    cmd_create(SimpleNamespace(name="dupe", package=None, template="default"))
    # Existing dir untouched (no enpaf.json written into it).
    assert not (tmp_path / "dupe" / "enpaf.json").exists()


# ─── argument parsing / dispatch ──────────────────────────────

def test_no_command_prints_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["paf"])
    main()  # must not raise
    out = capsys.readouterr().out.lower()
    assert "create" in out
    assert "build" in out


def test_build_requires_target(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["paf", "build"])
    with pytest.raises(SystemExit):
        main()


def test_build_rejects_bad_target(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["paf", "build", "exe"])
    with pytest.raises(SystemExit):
        main()


def test_create_via_main_dispatch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["paf", "create", "dispatchapp"])
    main()
    assert (tmp_path / "dispatchapp" / "enpaf.json").is_file()


def test_build_in_non_project_dir_exits_cleanly(tmp_path, monkeypatch):
    # No enpaf.json -> cmd_build should report and return, not crash/build.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["paf", "build", "apk"])
    main()  # returns without raising
