"""Tests for the build tooling helpers (CLI build + ProjectGenerator).

These cover the pure logic — OneDrive detection, build-dir relocation, Java
version parsing and file-safety helpers — without invoking Gradle/Chaquopy.
"""

import os

import pytest

from enpaf.cli.commands import build as build_cmd
from enpaf.builder.project_generator import (
    ProjectGenerator,
    safe_copy,
    safe_rmtree,
)


# ─── OneDrive detection ───────────────────────────────────────

def test_under_onedrive_substring(monkeypatch):
    for v in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        monkeypatch.delenv(v, raising=False)
    inside = os.sep.join(["", "Users", "me", "OneDrive", "proj"])
    outside = os.sep.join(["", "dev", "code", "proj"])
    assert build_cmd._under_onedrive(inside) is True
    assert build_cmd._under_onedrive(outside) is False


def test_under_onedrive_env_root(monkeypatch, tmp_path):
    root = tmp_path / "ODroot"
    root.mkdir()
    monkeypatch.setenv("OneDrive", str(root))
    assert build_cmd._under_onedrive(str(root / "myapp")) is True


# ─── Build-dir relocation ─────────────────────────────────────

def test_resolve_build_dir_honors_override(monkeypatch, tmp_path):
    builds = tmp_path / "builds"
    monkeypatch.setenv("ENPAF_BUILD_DIR", str(builds))
    result = build_cmd._resolve_build_dir(str(tmp_path / "myproj"))
    assert str(builds) in result
    assert os.path.basename(result).startswith("myproj-")


def test_resolve_build_dir_local_when_not_onedrive(monkeypatch, tmp_path):
    monkeypatch.delenv("ENPAF_BUILD_DIR", raising=False)
    for v in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        monkeypatch.delenv(v, raising=False)
    proj = tmp_path / "plainproj"
    result = build_cmd._resolve_build_dir(str(proj))
    assert result == os.path.join(str(proj), ".enpaf_build")


def test_resolve_build_dir_relocates_under_onedrive(monkeypatch, tmp_path):
    monkeypatch.delenv("ENPAF_BUILD_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    proj = tmp_path / "OneDrive" / "myproj"
    monkeypatch.setenv("OneDrive", str(tmp_path / "OneDrive"))
    result = build_cmd._resolve_build_dir(str(proj))
    assert "enpaf" in result and "builds" in result
    assert ".enpaf_build" not in result  # must NOT build inside OneDrive


# ─── Java version parsing ─────────────────────────────────────

class _FakeProc:
    def __init__(self, stderr="", stdout=""):
        self.stderr = stderr
        self.stdout = stdout


@pytest.mark.parametrize(
    "text,expected",
    [
        ('openjdk version "17.0.9" 2023-10-17', 17),
        ('openjdk version "21" 2023-09-19', 21),
        ('java version "1.8.0_381"', 8),
        ('openjdk version "11.0.20" 2023', 11),
    ],
)
def test_java_major_version_parsing(monkeypatch, text, expected):
    monkeypatch.setattr(build_cmd.subprocess, "run",
                        lambda *a, **k: _FakeProc(stderr=text))
    assert build_cmd._java_major_version("java") == expected


def test_java_major_version_unparseable(monkeypatch):
    monkeypatch.setattr(build_cmd.subprocess, "run",
                        lambda *a, **k: _FakeProc(stderr="not a version"))
    assert build_cmd._java_major_version("java") is None


def test_java_major_version_handles_subprocess_failure(monkeypatch):
    def _raise(*a, **k):
        raise OSError("no java")

    monkeypatch.setattr(build_cmd.subprocess, "run", _raise)
    assert build_cmd._java_major_version("java") is None


# ─── ProjectGenerator pure bits ───────────────────────────────

def test_wrapper_tag_format():
    gen = ProjectGenerator("proj", {}, "out")
    assert gen._wrapper_tag() == "v8.4.0"


def test_generator_records_release_flag():
    gen = ProjectGenerator("proj", {}, "out", release=True, keystore_path="ks.jks")
    assert gen.release is True
    assert gen.keystore_path == "ks.jks"


# ─── File-safety helpers (Windows/OneDrive resilience) ────────

def test_safe_copy_overwrites_readonly(tmp_path):
    import stat

    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("new", encoding="utf-8")
    dst.write_text("old", encoding="utf-8")
    os.chmod(dst, stat.S_IREAD)  # read-only, like a OneDrive placeholder
    safe_copy(str(src), str(dst))
    assert dst.read_text(encoding="utf-8") == "new"


def test_safe_rmtree_removes_tree(tmp_path):
    root = tmp_path / "tree"
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "f.txt").write_text("x", encoding="utf-8")
    safe_rmtree(str(root))
    assert not root.exists()


def test_safe_rmtree_missing_path_is_noop(tmp_path):
    safe_rmtree(str(tmp_path / "does_not_exist"))  # must not raise
