"""Unit-tier pytest fixtures.

Component tests that need a database use a fresh production in-memory manager.
Tests that need a runtime ask for ``unit_runtime_context``. Pure tests request
neither, and nothing here loads installed plugins for them.
"""

from __future__ import annotations

from pathlib import Path

import logging

import pytest

import colosseum.context as context_module
from colosseum.database.manager import DatabaseManager
from colosseum.logging.setup import _detach_handlers


@pytest.fixture
def db() -> DatabaseManager:
    manager = DatabaseManager()
    manager.initialize(Path(":memory:"))
    try:
        yield manager
    finally:
        manager.close()


@pytest.fixture
def unit_runtime_context(tmp_path: Path):
    ctx = context_module.init_context(test_case_name="unit")
    ctx.output_dir = tmp_path
    # Memory storage is enough for component tests. Leave runtime_ready false so
    # the first evidence call still attaches logging through the real startup path.
    ctx.db.initialize(Path(":memory:"))
    try:
        yield ctx
    finally:
        if isinstance(ctx.logger, logging.Logger):
            _detach_handlers(ctx.logger)
            ctx.logger = None
        if ctx.db.is_initialized():
            ctx.db.close()


@pytest.fixture
def io_bench(tmp_path: Path):
    """Write a config TOML snippet under ``tmp_path`` and return its path."""

    def _write(body: str) -> Path:
        path = tmp_path / "config.toml"
        path.write_text(body.strip() + "\n", encoding="utf-8")
        return path

    return _write
