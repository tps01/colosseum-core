"""Unit tests for freeze packaging helpers (no PyInstaller run)."""

from __future__ import annotations

import stat
import sys
import tarfile
import zipfile
from importlib import resources
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from colosseum.tools import build_executable as build_executable_mod
from colosseum.tools.build_executable import (
    _launcher_name,
    _plugin_package_path_roots,
    archive_app,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_hook_is_packaged_as_resource() -> None:
    hook = resources.files("colosseum").joinpath("hooks", "hook-colosseum.py")
    assert hook.is_file()


def test_plugin_package_path_roots_dedupes_and_skips_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root_a = tmp_path / "plugin_a"
    root_b = tmp_path / "plugin_b"
    root_a.mkdir()
    root_b.mkdir()

    eps = [
        SimpleNamespace(value="plugin_a:register"),
        SimpleNamespace(value="plugin_a.api:register"),
        SimpleNamespace(value="plugin_b:register"),
        SimpleNamespace(value="missing_plugin:register"),
    ]
    monkeypatch.setattr(
        build_executable_mod,
        "_discovered_for_group",
        lambda _group: eps,
    )

    def fake_get_package_paths(name: str) -> tuple[str, str]:
        mapping = {
            "plugin_a": (str(root_a), str(root_a / "plugin_a")),
            "plugin_b": (str(root_b), str(root_b / "plugin_b")),
        }
        if name not in mapping:
            raise ValueError(name)
        return mapping[name]

    import PyInstaller.utils.hooks as hooks_mod

    monkeypatch.setattr(hooks_mod, "get_package_paths", fake_get_package_paths)

    assert _plugin_package_path_roots() == [str(root_a), str(root_b)]


def _fake_app_dir(tmp_path: Path) -> Path:
    app_dir = tmp_path / "colosseum"
    app_dir.mkdir()
    launcher = app_dir / _launcher_name()
    launcher.write_text("launcher", encoding="utf-8")
    internal = app_dir / "_internal"
    internal.mkdir()
    (internal / "payload.txt").write_text("payload", encoding="utf-8")
    return app_dir


def test_archive_app_zip(tmp_path: Path) -> None:
    app_dir = _fake_app_dir(tmp_path)
    archive = archive_app(app_dir, kind="zip")
    assert archive.name == "colosseum.zip"
    assert archive.is_file()
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
    assert f"colosseum/{_launcher_name()}" in names
    assert "colosseum/_internal/payload.txt" in names


def test_archive_app_gztar(tmp_path: Path) -> None:
    app_dir = _fake_app_dir(tmp_path)
    launcher = app_dir / _launcher_name()
    mode = launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    launcher.chmod(mode)

    archive = archive_app(app_dir, kind="gztar")
    assert archive.name == "colosseum.tar.gz"
    assert archive.is_file()
    with tarfile.open(archive, "r:gz") as tf:
        names = set(tf.getnames())
        member = tf.getmember(f"colosseum/{_launcher_name()}")
    assert f"colosseum/{_launcher_name()}" in names
    assert "colosseum/_internal/payload.txt" in names
    assert member.mode & stat.S_IXUSR


def test_archive_app_missing_launcher(tmp_path: Path) -> None:
    app_dir = tmp_path / "colosseum"
    app_dir.mkdir()
    (app_dir / "_internal").mkdir()
    with pytest.raises(SystemExit, match="_internal"):
        archive_app(app_dir, kind="zip")


def test_archive_app_missing_internal(tmp_path: Path) -> None:
    app_dir = tmp_path / "colosseum"
    app_dir.mkdir()
    (app_dir / _launcher_name()).write_text("launcher", encoding="utf-8")
    with pytest.raises(SystemExit, match="_internal"):
        archive_app(app_dir, kind="zip")


def test_default_archive_kind_matches_platform(tmp_path: Path) -> None:
    app_dir = _fake_app_dir(tmp_path)
    archive = archive_app(app_dir)
    if sys.platform == "win32":
        assert archive.suffix == ".zip"
    else:
        assert archive.name.endswith(".tar.gz")
