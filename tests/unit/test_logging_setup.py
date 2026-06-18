"""Logging setup: file + console handlers."""

from __future__ import annotations

import logging

from colosseum.logging.setup import setup_logging


def test_setup_logging_console_info_filters_debug(unit_runtime_context, capsys) -> None:
    logger = setup_logging(
        unit_runtime_context,
        console=True,
        console_level=logging.INFO,
    )
    logger.debug("hidden debug")
    logger.info("visible info")

    out = capsys.readouterr().out
    assert "visible info" in out
    assert "hidden debug" not in out


def test_setup_logging_console_debug_shows_debug(unit_runtime_context, capsys) -> None:
    logger = setup_logging(
        unit_runtime_context,
        console=True,
        console_level=logging.DEBUG,
    )
    logger.debug("visible debug")

    out = capsys.readouterr().out
    assert "visible debug" in out
