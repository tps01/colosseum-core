from __future__ import annotations

import argparse
import faulthandler
import sys
from pathlib import Path

from colosseum.config import ConfigError, load_config
from colosseum.context import init_context
from colosseum.database.evidence_import import import_evidence_from_previous
from colosseum.results.exit_policy import endex
from colosseum.runner.command_invoke import (
    CommandInvokeError,
    command_logical_name,
    invoke_plugin_commands,
)
from colosseum.runner.provenance import record_single_provenance
from colosseum.runner.run_options import (
    RunOptions,
    RunOptionsError,
    resolve_execution_mode,
    resolve_input_path,
)
from colosseum.runner.runtime import OutputNotWritableError, ensure_runtime_ready

from .single_test import ScriptRunError, run_script
from .suite import SuiteError, run_suite

_DESCRIPTION = (
    "Colosseum test automation: run Python test scripts and suites with configuration."
)
_EPILOG = """examples:
  colosseum run my_test.py -g config.toml
  colosseum run -c template.arm_device,key=dev1 -g config.toml
  colosseum run-suite suite.toml -g config.toml -d
  colosseum --gui
"""


def _add_shared_run_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-i",
        "--input-dir",
        dest="input_dir",
        metavar="PATH",
        type=Path,
        help="Base directory for the positional test or suite path",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        dest="output_dir",
        metavar="PATH",
        type=Path,
        help="Directory where timestamped run output folders are created",
    )
    parser.add_argument(
        "-g",
        "--config",
        dest="config_path",
        metavar="PATH",
        help="TOML configuration consumed by installed plugins",
    )
    parser.add_argument(
        "-m",
        "--metadata",
        dest="metadata_path",
        metavar="PATH",
        help="Metadata YAML (test_metadata block)",
    )
    parser.add_argument(
        "--parameters",
        dest="parameters_path",
        metavar="PATH",
        type=Path,
        help="Parameters TOML (limits and per-key kwargs) for this run or suite",
    )
    parser.add_argument(
        "--report",
        dest="reports",
        action="append",
        default=None,
        metavar="NAME",
        help="Enable a report listener (wats, junit); repeatable. Replaces [colosseum.reports]",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Include DEBUG logs on stdout",
    )
    parser.add_argument(
        "--no-artifacts",
        action="store_true",
        help="Skip outputs/, debug.log, and on-disk execution.sqlite (utility/script mode)",
    )


def _add_execution_mode_options(
    parser: argparse.ArgumentParser,
    *,
    allow_verify_only: bool,
) -> None:
    mode_choices: tuple[str, ...] = (
        ("full", "procedure", "verify_only") if allow_verify_only else ("full", "procedure")
    )
    parser.add_argument(
        "--mode",
        dest="execution_mode",
        choices=mode_choices,
        default=None,
        help=(
            "Execution mode: full (default), procedure, or verify_only"
            if allow_verify_only
            else "Execution mode: full (default) or procedure"
        ),
    )
    parser.add_argument(
        "-p",
        "--procedure",
        action="store_true",
        help="Alias for --mode procedure (commands/measurements only; skip verifications)",
    )
    if allow_verify_only:
        parser.add_argument(
            "-u",
            "--use-previous-output",
            dest="previous_output_dir",
            metavar="PATH",
            type=Path,
            help="Import prior measurements/commands and re-run verifications (verify_only)",
        )


def _add_run_only_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--show-faults",
        action="store_true",
        help="Enable faulthandler crash dumps for this run",
    )
    parser.add_argument(
        "-c",
        "--command",
        dest="plugin_commands",
        action="append",
        default=[],
        metavar="SPEC",
        help="Invoke a plugin @command (namespace.function,key=val,...); repeatable",
    )
    _add_execution_mode_options(parser, allow_verify_only=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="colosseum",
        description=_DESCRIPTION,
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--gui", action="store_true", help="Launch the desktop GUI runner")
    sub = parser.add_subparsers(dest="command", required=False)

    run_parser = sub.add_parser(
        "run",
        help="Run a single Python test file",
        description="Initialize runtime, call the script's main(), and finalize with col.endex().",
    )
    run_parser.add_argument(
        "test_file",
        nargs="?",
        help="Path to the Python test script (optional when -c is used)",
    )
    _add_shared_run_options(run_parser)
    _add_run_only_options(run_parser)

    suite_parser = sub.add_parser(
        "run-suite",
        help="Run a suite TOML (setup, tests, teardown)",
        description=(
            "Run setup scripts, test scripts, and teardown scripts in one output directory."
        ),
    )
    suite_parser.add_argument("suite_file", help="Path to the suite TOML file")
    _add_shared_run_options(suite_parser)
    _add_execution_mode_options(suite_parser, allow_verify_only=False)

    help_parser = sub.add_parser(
        "help",
        help="Show help for colosseum or a subcommand",
        description="Print usage for colosseum or a specific subcommand.",
    )
    help_parser.add_argument(
        "topic",
        nargs="?",
        choices=("run", "run-suite"),
        help="Subcommand to describe (default: top-level usage)",
    )
    return parser


def _print_help(parser: argparse.ArgumentParser, topic: str | None = None) -> None:
    if topic is None:
        parser.print_help()
        return
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            subparser = action.choices.get(topic)
            if subparser is not None:
                subparser.print_help()
                return
    parser.error(f"unknown help topic: {topic}")


def _load_run_config(config_path: str | None, metadata_path: str | None = None) -> None:
    from colosseum.context import get_context

    if config_path:
        load_config(config_path, metadata_path=metadata_path)
    elif metadata_path:
        from colosseum.config.metadata import load_metadata

        load_metadata(metadata_path)
    ctx = get_context()
    if config_path:
        ctx.session.config_pinned = True
    if metadata_path:
        ctx.session.metadata_pinned = True


def _shared_run_options(
    args: argparse.Namespace,
    *,
    command: str,
) -> RunOptions:
    """Resolve mode flags before any output-directory allocation."""
    previous_raw = getattr(args, "previous_output_dir", None)
    previous_path = Path(previous_raw).resolve() if previous_raw is not None else None
    execution_mode, previous_output_dir = resolve_execution_mode(
        command=command,  # type: ignore[arg-type]
        mode=getattr(args, "execution_mode", None),
        procedure=bool(getattr(args, "procedure", False)),
        previous_output=previous_path,
    )

    outputs_root = None
    if getattr(args, "output_dir", None) is not None:
        outputs_root = Path(args.output_dir).resolve()
    report_cli = getattr(args, "reports", None)
    parameters_raw = getattr(args, "parameters_path", None)
    return RunOptions(
        input_dir=Path(args.input_dir).resolve() if getattr(args, "input_dir", None) else None,
        outputs_root=outputs_root,
        execution_mode=execution_mode,
        previous_output_dir=previous_output_dir,
        plugin_commands=list(getattr(args, "plugin_commands", []) or []),
        show_faults=bool(getattr(args, "show_faults", False)),
        parameters_path=Path(parameters_raw).resolve() if parameters_raw is not None else None,
        report_cli=list(report_cli) if report_cli is not None else None,
    )


def _maybe_enable_faulthandler(*, show_faults: bool) -> None:
    if show_faults:
        faulthandler.enable()


def _import_previous_evidence(ctx: object, run_options: RunOptions) -> None:
    if run_options.execution_mode != "verify_only":
        return
    if run_options.previous_output_dir is None:
        raise RuntimeError("verify_only mode requires --use-previous-output")
    import_evidence_from_previous(ctx, run_options.previous_output_dir)


def _run_single_test(
    test_path: Path | None,
    config_path: str | None,
    metadata_path: str | None,
    *,
    debug: bool = False,
    no_artifacts: bool = False,
    run_options: RunOptions | None = None,
) -> None:
    options = run_options or RunOptions()
    logical_name = test_path.stem if test_path is not None else command_logical_name(
        options.plugin_commands[0],
    )
    ctx = init_context(
        test_case_name=logical_name,
        config_path=Path(config_path).resolve() if config_path else None,
        metadata_path=Path(metadata_path).resolve() if metadata_path else None,
        no_artifacts=no_artifacts,
        run_options=options,
    )
    ctx.debug_logging = debug
    ctx.active_execution_mode = options.execution_mode
    _load_run_config(config_path, metadata_path)
    ensure_runtime_ready(ctx)
    from colosseum.config.parameters import (
        ParametersError,
        attach_parameters,
        resolve_parameters_path,
    )
    from colosseum.results.reports import apply_enabled_reports

    apply_enabled_reports(ctx)
    resolved_parameters = resolve_parameters_path(
        script_path=test_path,
        cli_path=options.parameters_path,
    )
    try:
        attach_parameters(
            ctx,
            resolved_parameters,
            required=options.parameters_path is not None,
        )
    except ParametersError as exc:
        record_single_provenance(ctx, test_path, resolved_parameters)
        ctx.result_aggregator.mark_suite_error(str(exc))
        if ctx.logger is not None:
            ctx.logger.error("Parameters load failed: %s", exc)
        endex()
        return
    record_single_provenance(ctx, test_path, resolved_parameters)
    _import_previous_evidence(ctx, options)
    try:
        if options.plugin_commands:
            invoke_plugin_commands(ctx, options.plugin_commands)
        if test_path is not None:
            run_script(test_path)
    except (ScriptRunError, CommandInvokeError):
        ctx.result_aggregator.mark_suite_error("test script failed")
    except Exception as exc:
        ctx.result_aggregator.mark_suite_error(f"test run failed: {exc}")
        if ctx.logger is not None:
            ctx.logger.exception("Unhandled error during test run")
    finally:
        endex()


def _exit_with_message(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1) from None


def run_cli(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.gui:
        from colosseum.gui.app import main as gui_main

        gui_main()
        return 0

    if args.command is None:
        _print_help(parser)
        return 0

    if args.command == "help":
        _print_help(parser, getattr(args, "topic", None))
        return 0

    if args.command == "run":
        try:
            run_options = _shared_run_options(args, command="run")
        except RunOptionsError as exc:
            _exit_with_message(str(exc))
        _maybe_enable_faulthandler(show_faults=run_options.show_faults)
        if not args.test_file and not run_options.plugin_commands:
            parser.error("run requires a test_file and/or at least one -c/--command")
        test_path = None
        if args.test_file:
            test_path = resolve_input_path(run_options.input_dir, args.test_file)
            if not test_path.exists():
                _exit_with_message(f"Test file not found: {test_path}")
        try:
            _run_single_test(
                test_path,
                args.config_path,
                getattr(args, "metadata_path", None),
                debug=bool(args.debug),
                no_artifacts=bool(getattr(args, "no_artifacts", False)),
                run_options=run_options,
            )
        except (ConfigError, OutputNotWritableError) as exc:
            _exit_with_message(str(exc))
        return 0

    if args.command == "run-suite":
        try:
            run_options = _shared_run_options(args, command="run-suite")
        except RunOptionsError as exc:
            _exit_with_message(str(exc))
        suite_path = resolve_input_path(run_options.input_dir, args.suite_file)
        if not suite_path.exists():
            _exit_with_message(f"Suite file not found: {suite_path}")
        try:
            config = Path(args.config_path).resolve() if args.config_path else None
            run_suite(
                suite_path,
                config,
                metadata_path=Path(args.metadata_path).resolve() if args.metadata_path else None,
                debug=bool(args.debug),
                no_artifacts=bool(getattr(args, "no_artifacts", False)),
                run_options=run_options,
            )
        except (ConfigError, SuiteError, OutputNotWritableError) as exc:
            _exit_with_message(str(exc))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 1


def main(argv: list[str] | None = None) -> None:
    try:
        sys.exit(run_cli(argv))
    except SystemExit as exc:
        raise exc


if __name__ == "__main__":
    main()
