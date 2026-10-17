"""CLI run options shared by single-test and suite runners."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

ExecutionMode = Literal["full", "procedure", "verify_only"]
_ALLOWED_MODES: frozenset[str] = frozenset({"full", "procedure", "verify_only"})


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


def resolve_input_path(input_dir: Path | None, positional: str) -> Path:
    """Resolve a positional test/suite path against an optional input directory."""
    path = Path(positional)
    if input_dir is not None:
        path = input_dir / path
    return path.resolve()


def resolve_outputs_root(options: RunOptions) -> Path:
    """Return the directory where timestamped run folders are created."""
    if options.outputs_root is not None:
        return options.outputs_root
    return Path.cwd() / "outputs"


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
