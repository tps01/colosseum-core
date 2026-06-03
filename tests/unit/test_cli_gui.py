"""CLI --gui flag parsing."""

from __future__ import annotations

from colosseum.runner.cli import _build_parser, run_cli


def test_build_parser_accepts_gui_without_subcommand() -> None:
    args = _build_parser().parse_args(["--gui"])
    assert args.gui is True
    assert args.command is None


def test_run_cli_requires_subcommand_without_gui() -> None:
    try:
        run_cli([])
        raised = False
    except SystemExit as exc:
        raised = exc.code != 0
    assert raised
