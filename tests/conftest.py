"""Shared pytest fixtures for Colosseum test tiers."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

import pytest

import colosseum.context as context_module
from colosseum.database.manager import DatabaseManager
from colosseum.database.schema import SCHEMA_SQL

from tests.db_unit import UNIT_TEST_DB_URI, connect_unit_test_db, truncate_unit_test_db

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def unit_test_db() -> sqlite3.Connection:
    # Hold one connection open so shared in-memory schema survives the session.
    keeper = sqlite3.connect(UNIT_TEST_DB_URI, uri=True)
    keeper.executescript(SCHEMA_SQL)
    keeper.commit()
    yield keeper
    keeper.close()


@pytest.fixture(scope="session")
def unit_test_db_uri(unit_test_db: sqlite3.Connection) -> str:
    return UNIT_TEST_DB_URI


@pytest.fixture
def db(unit_test_db: sqlite3.Connection, unit_test_db_uri: str) -> DatabaseManager:
    truncate_unit_test_db(unit_test_db)
    manager = DatabaseManager()
    connect_unit_test_db(manager, unit_test_db_uri)
    try:
        yield manager
    finally:
        manager.close()
        truncate_unit_test_db(unit_test_db)


BENCH_SIM = REPO_ROOT / "examples" / "configs" / "bench.sim.toml"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


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
def unit_runtime_context(
    tmp_path: Path,
    unit_test_db: sqlite3.Connection,
    unit_test_db_uri: str,
) -> context_module.RuntimeContext:
    truncate_unit_test_db(unit_test_db)
    ctx = context_module.init_context(test_case_name="unit")
    ctx.output_dir = tmp_path
    connect_unit_test_db(ctx.db, unit_test_db_uri)
    try:
        yield ctx
    finally:
        ctx.db.close()
        truncate_unit_test_db(unit_test_db)


@pytest.fixture
def subprocess_env(repo_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    env["COLOSSEUM_BENCH_CONFIG"] = "bench.sim.toml"
    return env


def run_endex_expect_code(expected: int) -> None:
    from colosseum.results import endex

    with pytest.raises(SystemExit) as exc_info:
        endex()
    code = exc_info.value.code
    if code is None:
        code = 0
    assert code == expected, f"expected exit {expected}, got {code}"


def latest_output_dir(cwd: Path) -> Path:
    outputs = cwd / "outputs"
    assert outputs.is_dir(), f"outputs/ was not created under {cwd}"
    runs = sorted(outputs.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    assert runs, f"outputs/ is empty under {cwd}"
    return runs[0]


def query_db(run_dir: Path, sql: str, params: tuple = ()) -> list[tuple[Any, ...]]:
    db_path = run_dir / "execution.sqlite"
    assert db_path.is_file(), f"missing database in {run_dir}"
    conn = sqlite3.connect(db_path)
    try:
        return list(conn.execute(sql, params).fetchall())
    finally:
        conn.close()


def verification_row(run_dir: Path, key: str) -> tuple[Any, ...] | None:
    rows = query_db(
        run_dir,
        "SELECT status, optional, domain FROM verifications WHERE key=? ORDER BY id DESC LIMIT 1",
        (key,),
    )
    return rows[0] if rows else None
