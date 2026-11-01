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
    if command != "run" and export is not None:
        raise RunOptionsError("--export is only supported by colosseum run")
    if dry_run and export is not None:
        raise RunOptionsError("--dry-run cannot be combined with --export")
    if mode is not None or procedure or previous_output is not None:
        raise RunOptionsError(
            "--dry-run and --export cannot be combined with --mode, -p/--procedure, "
            "or -u/--use-previous-output",
        )
    if no_artifacts:
        raise RunOptionsError(
            "--dry-run and --export cannot be combined with --no-artifacts",
        )
    if export is None:
        return
    if not has_test_file:
        raise RunOptionsError("--export parameters requires a test file")
    if plugin_commands:
        raise RunOptionsError("--export cannot be combined with -c/--command")
    if parameters_path is not None:
        raise RunOptionsError("--export cannot be combined with --parameters")


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
        if mode == "verify_only" or has_previous:
            raise RunOptionsError(
                "run-suite does not support verify_only / --use-previous-output; "
                "use colosseum run for evidence re-verification",
            )
        if procedure and mode is not None and mode != "procedure":
            raise RunOptionsError(
                f"--mode {mode} conflicts with -p/--procedure; they must agree",
            )
        if mode == "procedure" or (mode is None and procedure):
            return "procedure", None
        return "full", None

    # --- single run ---
    if mode is None:
        if procedure and has_previous:
            raise RunOptionsError(
                "-p/--procedure cannot be combined with --use-previous-output",
            )
        if procedure:
            return "procedure", None
        if has_previous:
            return "verify_only", previous_output
        return "full", None

    if mode == "full":
        if procedure:
            raise RunOptionsError(
                "--mode full conflicts with -p/--procedure; omit -p or use --mode procedure",
            )
        if has_previous:
            raise RunOptionsError(
                "--mode full cannot be combined with --use-previous-output",
            )
        return "full", None

    if mode == "procedure":
        if has_previous:
            raise RunOptionsError(
                "--mode procedure cannot be combined with --use-previous-output",
            )
        # -p with --mode procedure is fine (agree)
        return "procedure", None

    # mode == verify_only
    if procedure:
        raise RunOptionsError(
            "--mode verify_only conflicts with -p/--procedure",
        )
    if not has_previous:
        raise RunOptionsError(
            "--mode verify_only requires --use-previous-output PATH",
        )
    return "verify_only", previous_output
