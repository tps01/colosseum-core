"""Pytest fixtures shared across unit, integration, and e2e tiers."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import colosseum.context as context_module

from tests.support.helpers import BENCH_SIM, FIXTURES, REPO_ROOT


@pytest.fixture(autouse=True)
def _reset_runtime_context() -> None:
    context_module._ACTIVE_CONTEXT = None
    yield
    context_module._ACTIVE_CONTEXT = None


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def bench_sim() -> Path:
    assert BENCH_SIM.is_file(), f"missing bench sim config: {BENCH_SIM}"
    return BENCH_SIM


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
    env["PYTHONPATH"] = str(repo_root)
    env["COLOSSEUM_BENCH_CONFIG"] = "bench.sim.toml"
    return env
