from __future__ import annotations

from pathlib import Path
from typing import List

from .records import MeasurementRecord, RunMetadataRecord, VerificationRecord


def _ctx():
    from ..context import require_context

    return require_context()

_ALLOWED_TABLES = frozenset({"measurements", "verifications", "events", "artifacts", "run_metadata"})


def is_allowed_table(name: str) -> bool:
    return name in _ALLOWED_TABLES or name.startswith("plugin_")


def read_measurements() -> List[MeasurementRecord]:
    ctx = _ctx()
    if not ctx.db.is_initialized():
        raise RuntimeError("Database is not initialized for this run")
    return ctx.db.fetch_all_measurements()


def read_verifications() -> List[VerificationRecord]:
    ctx = _ctx()
    if not ctx.db.is_initialized():
        raise RuntimeError("Database is not initialized for this run")
    return ctx.db.fetch_all_verifications()


def read_run_metadata() -> List[RunMetadataRecord]:
    ctx = _ctx()
    if not ctx.db.is_initialized():
        raise RuntimeError("Database is not initialized for this run")
    return ctx.db.fetch_run_metadata()


def read_table(name: str) -> List[dict]:
    ctx = _ctx()
    if not ctx.db.is_initialized():
        raise RuntimeError("Database is not initialized for this run")
    if is_allowed_table(name):
        return ctx.db.fetch_table_rows(name)
    raise ValueError(f"Unknown or disallowed table: {name}")
