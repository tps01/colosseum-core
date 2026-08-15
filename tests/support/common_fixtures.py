"""Pytest fixtures shared across unit, integration, and e2e tiers."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import colosseum.context as context_module

from tests.support.helpers import CORE_CONFIG, FIXTURES, REPO_ROOT


@pytest.fixture(autouse=True)
def _reset_runtime_context() -> None:
    context_module._ACTIVE_CONTEXT = None
    yield
    context_module._ACTIVE_CONTEXT = None


@pytest.fixture(autouse=True)
def _defer_db_commits_in_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Batch SQLite commits during pytest; flushed at endex/close (not in CLI subprocess)."""
    monkeypatch.setenv("COLOSSEUM_DEFER_DB_COMMITS", "1")


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def core_config() -> Path:
    assert CORE_CONFIG.is_file(), f"missing core config: {CORE_CONFIG}"
    return CORE_CONFIG


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def subprocess_env(repo_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("COLOSSEUM_DEFER_DB_COMMITS", None)
    env["PYTHONPATH"] = str(repo_root)
    return env
