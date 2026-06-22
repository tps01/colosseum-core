from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from ..context import RuntimeContext
from ..database import initialize_database_if_needed
from ..logging import setup_logging

_NO_ARTIFACTS_OUTPUT_ERROR = (
    "Output directory is unavailable in no-artifacts mode; "
    "disable no_artifacts or use persisted output for file artifacts."
)


def sanitize_logical_name(logical_name: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]", "_", logical_name).strip("_")
    if not value:
        value = "run"
    return value[:64]


def allocate_run_directory(cwd: Path, logical_name: str) -> Path:
    outputs_root = cwd / "outputs"
    outputs_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_name = f"{stamp}_{sanitize_logical_name(logical_name)}"
    candidate = outputs_root / run_name
    suffix = 1
    while candidate.exists():
        candidate = outputs_root / f"{run_name}_{suffix}"
        suffix += 1
    return candidate


def _logical_output_name(ctx: RuntimeContext) -> str:
    return ctx.suite_name or ctx.test_case_name


def ensure_runtime_ready(ctx: RuntimeContext, logical_name: str | None = None) -> None:
    """Bootstrap logging and database for the active run (idempotent)."""
    if ctx.runtime_ready:
        return
    if logical_name is None:
        logical_name = _logical_output_name(ctx)
    console_level = logging.DEBUG if ctx.debug_logging else logging.INFO
    if ctx.no_artifacts:
        ctx.logger = setup_logging(ctx, console=True, console_level=console_level, file=False)
        ctx.logger.debug("Runtime ready (no-artifacts mode)")
        initialize_database_if_needed(ctx)
    else:
        output_dir = allocate_run_directory(Path.cwd(), logical_name)
        output_dir.mkdir(parents=True, exist_ok=True)
        ctx.output_dir = output_dir
        ctx.logger = setup_logging(ctx, console=True, console_level=console_level, file=True)
        ctx.logger.debug("Allocated output directory: %s", output_dir)
        initialize_database_if_needed(ctx)
    from ..config.loader import log_loaded_config

    if ctx.config is not None:
        log_loaded_config(ctx)
    for warning in ctx.config_warnings:
        if ctx.logger is not None:
            ctx.logger.warning(warning)
    ctx.runtime_ready = True


def ensure_output_dir(ctx: RuntimeContext, logical_name: str | None = None) -> Path:
    ensure_runtime_ready(ctx, logical_name)
    if ctx.no_artifacts or ctx.output_dir is None:
        raise RuntimeError(_NO_ARTIFACTS_OUTPUT_ERROR)
    return ctx.output_dir
