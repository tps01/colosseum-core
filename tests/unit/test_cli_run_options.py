"""CLI parser coverage for expanded run flags."""

from __future__ import annotations

import pytest

from colosseum.runner.cli import _build_parser, _shared_run_options
from colosseum.runner.run_options import RunOptionsError


def test_run_parser_accepts_shared_and_run_only_flags() -> None:
    args = _build_parser().parse_args(
        [
            "run",
            "pass_test.py",
            "-i",
            "./tests",
            "-o",
            "./runs",
            "-g",
            "config.toml",
            "-m",
            "meta.yaml",
            "-p",
            "--show-faults",
            "--parameters",
            "limits.toml",
            "--report",
            "wats",
            "--report",
            "junit",
        ],
    )
    assert args.command == "run"
    assert args.test_file == "pass_test.py"
    assert args.input_dir.name == "tests"
    assert args.output_dir.name == "runs"
    assert args.config_path == "config.toml"
    assert args.metadata_path == "meta.yaml"
    assert args.procedure is True
    assert args.show_faults is True
    assert args.parameters_path.name == "limits.toml"
    assert args.reports == ["wats", "junit"]
    options = _shared_run_options(args, command="run")
    assert options.execution_mode == "procedure"
    assert options.parameters_path is not None
    assert options.parameters_path.name == "limits.toml"
    assert options.report_cli == ["wats", "junit"]


def test_run_parser_without_report_leaves_report_cli_none() -> None:
    args = _build_parser().parse_args(["run", "pass_test.py", "-g", "config.toml"])
    options = _shared_run_options(args, command="run")
    assert options.report_cli is None
    assert options.parameters_path is None


def test_run_parser_rejects_removed_command_and_export_flags() -> None:
    for argv in (
        ["run", "-c", "stub.ping", "-g", "config.toml"],
        ["run", "pass_test.py", "--command", "stub.ping"],
        ["run", "pass_test.py", "--export", "parameters"],
    ):
        with pytest.raises(SystemExit):
            _build_parser().parse_args(argv)


def test_run_parser_requires_test_file() -> None:
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["run", "-g", "config.toml"])


def test_run_parser_rejects_procedure_and_previous_output_together() -> None:
    args = _build_parser().parse_args(
        ["run", "pass_test.py", "-p", "-u", "./prior", "-g", "config.toml"],
    )
    with pytest.raises(RunOptionsError, match="procedure"):
        _shared_run_options(args, command="run")


def test_run_parser_accepts_mode_procedure() -> None:
    args = _build_parser().parse_args(
        ["run", "pass_test.py", "--mode", "procedure", "-g", "config.toml"],
    )
    options = _shared_run_options(args, command="run")
    assert options.execution_mode == "procedure"


def test_run_parser_accepts_mode_verify_only_with_previous() -> None:
    args = _build_parser().parse_args(
        [
            "run",
            "pass_test.py",
            "--mode",
            "verify_only",
            "-u",
            "./prior",
            "-g",
            "config.toml",
        ],
    )
    options = _shared_run_options(args, command="run")
    assert options.execution_mode == "verify_only"
    assert options.previous_output_dir is not None


def test_suite_parser_has_shared_flags_and_procedure_only() -> None:
    args = _build_parser().parse_args(
        ["run-suite", "suite.toml", "-i", "./suites", "-o", "./runs", "-g", "config.toml", "-p"],
    )
    assert args.command == "run-suite"
    assert args.procedure is True
    options = _shared_run_options(args, command="run-suite")
    assert options.execution_mode == "procedure"


def test_run_parser_accepts_dry_run() -> None:
    dry = _build_parser().parse_args(["run", "pass_test.py", "--dry-run"])
    options = _shared_run_options(dry, command="run")
    assert options.dry_run is True


def test_run_parser_rejects_dry_run_combined_with_mode_or_no_artifacts() -> None:
    procedure = _build_parser().parse_args(["run", "pass_test.py", "--dry-run", "-p"])
    with pytest.raises(RunOptionsError, match="dry-run"):
        _shared_run_options(procedure, command="run")

    mode = _build_parser().parse_args(["run", "pass_test.py", "--dry-run", "--mode", "full"])
    with pytest.raises(RunOptionsError, match="--mode"):
        _shared_run_options(mode, command="run")

    previous = _build_parser().parse_args(
        ["run", "pass_test.py", "--dry-run", "-u", "./prior"],
    )
    with pytest.raises(RunOptionsError, match="use-previous-output"):
        _shared_run_options(previous, command="run")

    quiet = _build_parser().parse_args(["run", "pass_test.py", "--dry-run", "--no-artifacts"])
    with pytest.raises(RunOptionsError, match="no-artifacts"):
        _shared_run_options(quiet, command="run")


def test_suite_parser_accepts_dry_run_and_rejects_procedure() -> None:
    args = _build_parser().parse_args(["run-suite", "suite.toml", "--dry-run"])
    options = _shared_run_options(args, command="run-suite")
    assert options.dry_run is True

    combined = _build_parser().parse_args(["run-suite", "suite.toml", "--dry-run", "-p"])
    with pytest.raises(RunOptionsError, match="dry-run"):
        _shared_run_options(combined, command="run-suite")
    mode = _build_parser().parse_args(
        ["run-suite", "suite.toml", "--dry-run", "--mode", "full"],
    )
    with pytest.raises(RunOptionsError, match="--mode"):
        _shared_run_options(mode, command="run-suite")
    quiet = _build_parser().parse_args(
        ["run-suite", "suite.toml", "--dry-run", "--no-artifacts"],
    )
    with pytest.raises(RunOptionsError, match="no-artifacts"):
        _shared_run_options(quiet, command="run-suite")


def test_suite_parser_rejects_verify_only_mode() -> None:
    with pytest.raises(SystemExit):
        _build_parser().parse_args(
            ["run-suite", "suite.toml", "--mode", "verify_only", "-g", "config.toml"],
        )
