from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from ..context import RuntimeContext
from ..database import initialize_database_if_needed
from ..logging import setup_logging


def _sanitize(logical_name: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]", "_", logical_name).strip("_")
    if not value:
        value = "run"
    return value[:64]


def allocate_run_directory(cwd: Path, logical_name: str) -> Path:
    outputs_root = cwd / "outputs"
    outputs_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_name = f"{stamp}_{_sanitize(logical_name)}"
    candidate = outputs_root / run_name
    suffix = 1
    while candidate.exists():
        candidate = outputs_root / f"{run_name}_{suffix}"
        suffix += 1
    return candidate


def _logical_output_name(ctx: RuntimeContext) -> str:
    return ctx.suite_name or ctx.test_case_name


def ensure_output_dir(ctx: RuntimeContext, logical_name: str | None = None) -> Path:
    if logical_name is None:
        logical_name = _logical_output_name(ctx)
    if ctx.output_dir is None:
        output_dir = allocate_run_directory(Path.cwd(), logical_name)
        output_dir.mkdir(parents=True, exist_ok=True)
        ctx.output_dir = output_dir
        ctx.logger = setup_logging(ctx, console=ctx.verbose_logging)
        initialize_database_if_needed(ctx)
        for warning in ctx.config_warnings:
            ctx.logger.warning(warning)
    return ctx.output_dir
