from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..database.read_from_path import read_from_path
from ..database.records import VerificationRecord
from ..output.runs import (
    RunDirectoryEntry,
    list_run_directory_entries,
    read_summary_json,
)


@dataclass(frozen=True)
class RunBrowserRow:
    entry: RunDirectoryEntry
    status: str
    mtime: float


@dataclass(frozen=True)
class RunBrowserSnapshot:
    rows: list[RunBrowserRow]

    @property
    def output_dirs(self) -> set[Path]:
        return {row.entry.outputs_dir for row in self.rows}


@dataclass(frozen=True)
class DetailSnapshot:
    run_dir: Path
    table: str
    log_text: str | None = None
    log_error: str | None = None
    summary: dict[str, Any] | None = None
    table_rows: list[dict[str, object]] | None = None
    table_error: str | None = None
    verifications: list[VerificationRecord] | None = None
    verifications_error: str | None = None


def load_run_browser_snapshot(cwd: Path, *, max_depth: int = 2) -> RunBrowserSnapshot:
    rows: list[RunBrowserRow] = []
    for entry in list_run_directory_entries(cwd, max_depth=max_depth):
        try:
            mtime = entry.path.stat().st_mtime
        except OSError:
            continue
        try:
            summary = read_summary_json(entry.path)
        except (OSError, ValueError):
            summary = None
        status = "incomplete" if summary is None else str(summary.get("overall_result", "?"))
        rows.append(RunBrowserRow(entry=entry, status=status, mtime=mtime))
    return RunBrowserSnapshot(rows=rows)


def load_detail_snapshot(run_dir: Path, *, table: str, include_log: bool = True) -> DetailSnapshot:
    log_text: str | None = None
    log_error: str | None = None
    if include_log:
        log_path = run_dir / "debug.log"
        if not log_path.is_file():
            log_error = f"No debug.log in {run_dir.name}."
        else:
            try:
                log_text = log_path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                log_error = f"Cannot read debug.log: {exc}"

    try:
        summary = read_summary_json(run_dir)
    except (OSError, ValueError):
        summary = None
    table_rows: list[dict[str, object]] | None = None
    table_error: str | None = None
    verifications: list[VerificationRecord] | None = None
    verifications_error: str | None = None
    db_path = run_dir / "execution.sqlite"
    if not db_path.is_file():
        table_error = f"No execution.sqlite in {run_dir.name}."
        verifications_error = "No execution.sqlite."
    else:
        try:
            with read_from_path(db_path) as reader:
                table_rows = reader.read_table(table)
                verifications = reader.read_verifications()
        except (OSError, FileNotFoundError, ValueError) as exc:
            table_error = f"Cannot read {table}: {exc}"
            verifications_error = f"Cannot read database: {exc}"

    return DetailSnapshot(
        run_dir=run_dir,
        table=table,
        log_text=log_text,
        log_error=log_error,
        summary=summary,
        table_rows=table_rows,
        table_error=table_error,
        verifications=verifications,
        verifications_error=verifications_error,
    )
