"""Unit-tier pytest fixtures."""

from __future__ import annotations

import sqlite3

import pytest

import colosseum.context as context_module
from colosseum.database.manager import DatabaseManager
from colosseum.database.schema import SCHEMA_SQL

from tests.unit.db_unit import UNIT_TEST_DB_URI, connect_unit_test_db, truncate_unit_test_db

pytest_plugins = ["tests.support.common_fixtures"]


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


@pytest.fixture
def unit_runtime_context(
    tmp_path,
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
