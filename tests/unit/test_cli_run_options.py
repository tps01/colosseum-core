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
            "-c",
            "stub.ping,key=dev1",
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
    assert args.plugin_commands == ["stub.ping,key=dev1"]
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


def test_run_parser_allows_command_without_test_file() -> None:
    args = _build_parser().parse_args(["run", "-c", "stub.ping", "-g", "config.toml"])
    assert args.test_file is None
    assert args.plugin_commands == ["stub.ping"]


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
    assert not hasattr(args, "plugin_commands") or args.plugin_commands in ([], None)
    options = _shared_run_options(args, command="run-suite")
    assert options.execution_mode == "procedure"


def test_run_parser_accepts_dry_run_and_export() -> None:
    dry = _build_parser().parse_args(["run", "pass_test.py", "--dry-run"])
    dry_options = _shared_run_options(dry, command="run")
    assert dry_options.dry_run is True
    assert dry_options.export is None

    exported = _build_parser().parse_args(["run", "pass_test.py", "--export", "parameters"])
    export_options = _shared_run_options(exported, command="run")
    assert export_options.export == "parameters"
    assert export_options.dry_run is False


def test_run_parser_rejects_dry_run_combined_with_export_or_mode() -> None:
    both = _build_parser().parse_args(
        ["run", "pass_test.py", "--dry-run", "--export", "parameters"],
    )
    with pytest.raises(RunOptionsError, match="dry-run"):
        _shared_run_options(both, command="run")

    procedure = _build_parser().parse_args(
        ["run", "pass_test.py", "--export", "parameters", "-p"],
    )
    with pytest.raises(RunOptionsError, match="procedure"):
        _shared_run_options(procedure, command="run")

    previous = _build_parser().parse_args(
        ["run", "pass_test.py", "--dry-run", "-u", "./prior"],
    )
    with pytest.raises(RunOptionsError, match="use-previous-output"):
        _shared_run_options(previous, command="run")


def test_run_parser_rejects_export_without_a_script_or_with_parameters() -> None:
    missing = _build_parser().parse_args(["run", "--export", "parameters"])
    with pytest.raises(RunOptionsError, match="test file"):
        _shared_run_options(missing, command="run", has_test_file=False)

    limits = _build_parser().parse_args(
        ["run", "pass_test.py", "--export", "parameters", "--parameters", "limits.toml"],
    )
    with pytest.raises(RunOptionsError, match="--parameters"):
        _shared_run_options(limits, command="run")

    command = _build_parser().parse_args(
        ["run", "pass_test.py", "--export", "parameters", "-c", "stub.ping"],
    )
    with pytest.raises(RunOptionsError, match="--command"):
        _shared_run_options(command, command="run")


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
