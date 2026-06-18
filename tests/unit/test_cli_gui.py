"""CLI --gui flag, help, and argument parsing."""

from __future__ import annotations

import io
from contextlib import redirect_stdout

import pytest

from colosseum.runner.cli import _build_parser, run_cli


def test_build_parser_accepts_gui_without_subcommand() -> None:
    args = _build_parser().parse_args(["--gui"])
    assert args.gui is True
    assert args.command is None


def test_run_cli_without_subcommand_prints_help() -> None:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = run_cli([])
    assert code == 0
    assert "usage: colosseum" in buffer.getvalue()
    assert "run" in buffer.getvalue()


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_run_cli_top_level_help_exits_zero(flag: str) -> None:
    with pytest.raises(SystemExit) as exc:
        run_cli([flag])
    assert exc.value.code == 0


def test_run_cli_help_subcommand_exits_zero() -> None:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = run_cli(["help"])
    assert code == 0
    assert "usage: colosseum" in buffer.getvalue()


def test_run_cli_help_run_shows_run_usage() -> None:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = run_cli(["help", "run"])
    assert code == 0
    text = buffer.getvalue()
    assert "usage: colosseum run" in text
    assert "test_file" in text


def test_run_subcommand_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        run_cli(["run", "--help"])
    assert exc.value.code == 0
