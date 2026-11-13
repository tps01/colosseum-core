"""CLI --gui flag, help, and argument parsing."""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from types import ModuleType

import colosseum.runner.cli as cli
import pytest
from colosseum.runner.cli import _build_parser, run_cli


def test_build_parser_accepts_gui_without_subcommand() -> None:
    args = _build_parser().parse_args(["--gui"])
    assert args.gui is True
    assert args.command is None


def test_gui_delegates_and_returns_ui_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    root = ModuleType("colosseum_extensions")
    root.__path__ = []  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "colosseum_extensions", root)
    package = ModuleType("colosseum_extensions.ui")
    package.__path__ = []  # type: ignore[attr-defined]
    app = ModuleType("colosseum_extensions.ui.app")
    app.main = lambda: 7  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "colosseum_extensions.ui", package)
    monkeypatch.setitem(sys.modules, "colosseum_extensions.ui.app", app)
    assert run_cli(["--gui"]) == 7


@pytest.mark.parametrize(
    "missing_module", ["colosseum_extensions", "colosseum_extensions.ui", "colosseum_extensions.ui.app"],
)
def test_gui_reports_missing_ui(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], missing_module: str,
) -> None:
    def missing(_name: str) -> ModuleType:
        raise ModuleNotFoundError(f"No module named {missing_module!r}", name=missing_module)

    monkeypatch.setattr(cli, "import_module", missing)
    assert run_cli(["--gui"]) == 1
    assert "Install colosseum-extensions" in capsys.readouterr().err


def test_gui_propagates_missing_ui_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(_name: str) -> ModuleType:
        raise ModuleNotFoundError("No module named 'PySide6'", name="PySide6")

    monkeypatch.setattr(cli, "import_module", missing)
    with pytest.raises(ModuleNotFoundError, match="PySide6"):
        run_cli(["--gui"])


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
