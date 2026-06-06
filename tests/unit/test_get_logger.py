"""Tests for colosseum.logging.get_logger."""

from __future__ import annotations

from colosseum.logging import get_logger


def test_get_logger_returns_child_logger() -> None:
    logger = get_logger("colosseum.test.child")
    assert logger.name == "colosseum.test.child"
