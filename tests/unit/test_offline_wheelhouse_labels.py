"""Arch labels and wheel-arch checks for offline wheelhouse builds."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "ci" / "build_offline_wheelhouse.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_offline_wheelhouse", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_archive_format_windows_variants() -> None:
    mod = _load_module()
    assert mod._archive_format("windows") == "zip"
    assert mod._archive_format("windows-amd64") == "zip"
    assert mod._archive_format("linux-x86_64") == "gztar"
    assert mod._archive_format("linux-aarch64") == "gztar"


def test_assert_wheel_arches_rejects_cross_arch(tmp_path: Path) -> None:
    mod = _load_module()
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    (wheels / "pure-1.0-py3-none-any.whl").write_bytes(b"")
    (wheels / "bin-1.0-cp312-cp312-manylinux2014_x86_64.whl").write_bytes(b"")
    with pytest.raises(SystemExit, match="wrong-arch"):
        mod._assert_wheel_arches(wheels, os_label="linux-aarch64")


def test_assert_wheel_arches_accepts_matching(tmp_path: Path) -> None:
    mod = _load_module()
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    (wheels / "pure-1.0-py3-none-any.whl").write_bytes(b"")
    (wheels / "bin-1.0-cp312-cp312-manylinux2014_aarch64.whl").write_bytes(b"")
    mod._assert_wheel_arches(wheels, os_label="linux-aarch64")
