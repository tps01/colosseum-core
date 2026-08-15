"""Smoke tests for static analysis runner layout."""

from __future__ import annotations

from pathlib import Path

from tests.static._common import REPO, SCAN_PATHS, SCRIPTS_DIR, SOURCE_PACKAGES


def test_static_scan_paths_exist() -> None:
    for name in SCAN_PATHS:
        path = REPO / name
        assert path.is_dir(), f"missing scan path: {path}"


def test_static_repo_layout() -> None:
    assert (REPO / "tests" / "static" / "run_all.py").is_file()
    assert (REPO / "scripts" / "run_static.py").is_file()
    assert SCRIPTS_DIR.is_dir()
    assert len(SOURCE_PACKAGES) == 1
