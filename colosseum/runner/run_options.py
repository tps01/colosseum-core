"""CLI run options shared by single-test and suite runners."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

ExecutionMode = Literal["full", "procedure", "verify_only"]
ExportKind = Literal["parameters"]
_ALLOWED_MODES: frozenset[str] = frozenset({"full", "procedure", "verify_only"})
_ALLOWED_EXPORTS: frozenset[str] = frozenset({"parameters"})


class RunOptionsError(ValueError):
    """Invalid combination of execution-mode CLI flags."""


@dataclass
class RunOptions:
    input_dir: Path | None = None
    outputs_root: Path | None = None
    execution_mode: ExecutionMode = "full"
    previous_output_dir: Path | None = None
    plugin_commands: list[str] = field(default_factory=list)
    show_faults: bool = False
    parameters_path: Path | None = None
    # None means use [colosseum.reports] from config; a list (possibly empty)
    # means CLI --report replaced the table for this process.
    report_cli: list[str] | None = None
    dry_run: bool = False
    export: ExportKind | None = None


def resolve_input_path(input_dir: Path | None, positional: str) -> Path:
    """Resolve a positional test/suite path against an optional input directory."""
    from colosseum.paths import absolute_path

    path = Path(positional)
    if input_dir is not None:
        path = input_dir / path
    return absolute_path(path)


def resolve_outputs_root(options: RunOptions) -> Path:
    """Return the directory where timestamped run folders are created."""
    if options.outputs_root is not None:
        return options.outputs_root
    return Path.cwd() / "outputs"


def validate_run_flags(
    *,
    command: Literal["run", "run-suite"],
    dry_run: bool = False,
    export: str | None = None,
    mode: str | None = None,
    procedure: bool = False,
    previous_output: Path | None = None,
    plugin_commands: list[str] | None = None,
    parameters_path: Path | None = None,
    has_test_file: bool = True,
    no_artifacts: bool = False,
) -> None:
    """Reject ``--dry-run`` and ``--export`` combinations before a run folder exists."""
    if export is not None and export not in _ALLOWED_EXPORTS:
        raise RunOptionsError(
            f"Unknown --export {export!r}; expected one of: parameters",
        )
    if not dry_run and export is None:
        return

    # First matching rule wins. ``None`` message means accept / early return.
    rules: list[tuple[bool, str | None]] = [
        (
            command != "run" and export is not None,
            "--export is only supported by colosseum run",
        ),
        (dry_run and export is not None, "--dry-run cannot be combined with --export"),
        (
            mode is not None or procedure or previous_output is not None,
            "--dry-run and --export cannot be combined with --mode, -p/--procedure, "
            "or -u/--use-previous-output",
        ),
        (
            no_artifacts,
            "--dry-run and --export cannot be combined with --no-artifacts",
        ),
        (export is None, None),
        (not has_test_file, "--export parameters requires a test file"),
        (bool(plugin_commands), "--export cannot be combined with -c/--command"),
        (parameters_path is not None, "--export cannot be combined with --parameters"),
    ]
    for matches, message in rules:
        if not matches:
            continue
        if message is None:
            return
        raise RunOptionsError(message)


def resolve_execution_mode(
    *,
    command: Literal["run", "run-suite"],
    mode: str | None = None,
    procedure: bool = False,
    previous_output: Path | None = None,
) -> tuple[ExecutionMode, Path | None]:
    """Validate CLI mode flags and return ``(execution_mode, previous_output_dir)``.

    Call this before allocating output directories so misconfigured runs do not
    leave orphan folders. Hard errors beat silent flag drops.
    """
    if mode is not None and mode not in _ALLOWED_MODES:
        raise RunOptionsError(
            f"Unknown --mode {mode!r}; expected one of: full, procedure, verify_only",
        )

    has_previous = previous_output is not None
    if command == "run-suite":
        return _resolve_suite_execution_mode(
            mode=mode,
            procedure=procedure,
            has_previous=has_previous,
        )
    return _resolve_run_execution_mode(
        mode=mode,
        procedure=procedure,
        has_previous=has_previous,
        previous_output=previous_output,
    )


def _resolve_suite_execution_mode(
    *,
    mode: str | None,
    procedure: bool,
    has_previous: bool,
) -> tuple[ExecutionMode, Path | None]:
    rules: list[tuple[bool, str]] = [
        (
            mode == "verify_only" or has_previous,
            "run-suite does not support verify_only / --use-previous-output; "
            "use colosseum run for evidence re-verification",
        ),
        (
            procedure and mode is not None and mode != "procedure",
            f"--mode {mode} conflicts with -p/--procedure; they must agree",
        ),
    ]
    for matches, message in rules:
        if matches:
            raise RunOptionsError(message)
    if mode == "procedure" or (mode is None and procedure):
        return "procedure", None
    return "full", None


def _resolve_run_execution_mode(
    *,
    mode: str | None,
    procedure: bool,
    has_previous: bool,
    previous_output: Path | None,
) -> tuple[ExecutionMode, Path | None]:
    # Ordered decision table: first matching predicate wins.
    # str => raise RunOptionsError; tuple => return (mode, previous_dir).
    rules: list[tuple[bool, str | tuple[ExecutionMode, Path | None]]] = [
        (
            mode is None and procedure and has_previous,
            "-p/--procedure cannot be combined with --use-previous-output",
        ),
        (mode is None and procedure, ("procedure", None)),
        (mode is None and has_previous, ("verify_only", previous_output)),
        (mode is None, ("full", None)),
        (
            mode == "full" and procedure,
            "--mode full conflicts with -p/--procedure; omit -p or use --mode procedure",
        ),
        (
            mode == "full" and has_previous,
            "--mode full cannot be combined with --use-previous-output",
        ),
        (mode == "full", ("full", None)),
        (
            mode == "procedure" and has_previous,
            "--mode procedure cannot be combined with --use-previous-output",
        ),
        (mode == "procedure", ("procedure", None)),
        (
            mode == "verify_only" and procedure,
            "--mode verify_only conflicts with -p/--procedure",
        ),
        (
            mode == "verify_only" and not has_previous,
            "--mode verify_only requires --use-previous-output PATH",
        ),
        (mode == "verify_only", ("verify_only", previous_output)),
    ]
    for matches, outcome in rules:
        if not matches:
            continue
        if isinstance(outcome, str):
            raise RunOptionsError(outcome)
        return outcome
    raise RunOptionsError(f"Unknown --mode {mode!r}; expected one of: full, procedure, verify_only")
