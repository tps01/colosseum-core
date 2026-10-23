"""GUI run browser helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from colosseum.runner.runtime import (
    RunDirectoryEntry,
    list_run_directory_entries,
    read_summary_json,
)

if TYPE_CHECKING:
    from pathlib import Path


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
class RunSnapshot:
    run_dir: Path
    log_text: str | None = None
    log_error: str | None = None
    summary: dict[str, Any] | None = None


def load_run_browser_snapshot(cwd: Path, *, max_depth: int = 2) -> RunBrowserSnapshot:
    rows: list[RunBrowserRow] = []
    for entry in list_run_directory_entries(cwd, max_depth=max_depth):
        try:
            mtime = entry.path.stat().st_mtime
        except OSError:
            continue
        try:
            summary = read_summary_json(entry.path)
        except (OSError, ValueError, json.JSONDecodeError):
            summary = None
        rows.append(RunBrowserRow(entry=entry, status=display_status(summary), mtime=mtime))
    return RunBrowserSnapshot(rows=rows)


def load_run_snapshot(run_dir: Path) -> RunSnapshot:
    log_text: str | None = None
    log_error: str | None = None
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
    except (OSError, ValueError, json.JSONDecodeError):
        summary = None
    return RunSnapshot(run_dir=run_dir, log_text=log_text, log_error=log_error, summary=summary)


def display_status(summary: dict[str, Any] | None) -> str:
    """Run-list label. Crashes stay ERROR even when overall_result is FAIL."""
    if summary is None:
        return "incomplete"
    overall = str(summary.get("overall_result") or "")
    if overall.upper() == "ERROR":
        return "ERROR"
    if summary.get("suite_error"):
        return "ERROR"
    reason = str(summary.get("suite_fail_reason") or "")
    if "script_error" in reason:
        return "ERROR"
    if overall:
        return overall
    return "incomplete"


def _count_line(label: str, counts: object) -> str | None:
    if not isinstance(counts, dict) or not counts:
        return None
    parts = [f"{status} {count}" for status, count in sorted(counts.items())]
    total = sum(value for value in counts.values() if isinstance(value, int))
    return f"{label}: {total} ({', '.join(parts)})"


def format_summary_text(summary: dict[str, Any] | None) -> str:
    if summary is None:
        return "Summary unavailable. This run may be incomplete."
    lines = [
        f"Overall: {summary.get('overall_result', '?')} (exit {summary.get('exit_code')})",
        f"Test case: {summary.get('test_case')}",
        f"Suite: {summary.get('suite')}",
        f"Config: {summary.get('config_path')}",
        f"Output: {summary.get('output_directory')}",
        f"End time: {summary.get('end_time_utc')}",
    ]
    if summary.get("measurement_count") is not None:
        lines.append(f"Measurements: {summary.get('measurement_count')}")
    if summary.get("command_count") is not None:
        lines.append(f"Commands: {summary.get('command_count')}")
    verification_counts = summary.get("verification_counts") or {}
    command_counts = summary.get("command_counts") or {}
    if isinstance(verification_counts, dict):
        for label, key in (
            ("Verifications (required)", "required"),
            ("Verifications (optional)", "optional"),
        ):
            line = _count_line(label, verification_counts.get(key))
            if line:
                lines.append(line)
    if isinstance(command_counts, dict):
        for label, key in (
            ("Commands (required outcomes)", "required"),
            ("Commands (optional outcomes)", "optional"),
        ):
            line = _count_line(label, command_counts.get(key))
            if line:
                lines.append(line)
    if summary.get("suite_error"):
        lines.append(f"Suite error: {summary.get('suite_error')}")
    if summary.get("teardown_failed"):
        lines.append("Teardown failed: yes")
    if "suite_failed" in summary:
        lines.append(f"Suite failed: {'yes' if summary.get('suite_failed') else 'no'}")
    if summary.get("suite_fail_reason"):
        lines.append(f"Suite fail reason: {summary.get('suite_fail_reason')}")
    failed = summary.get("failed_required_verifications") or []
    if failed:
        lines.append("")
        lines.append("Failed required verifications:")
        for row in failed:
            lines.append(
                f"  - {row.get('status')} {row.get('domain')}.{row.get('command')} "
                f"key={row.get('key')}: {row.get('message')}",
            )
    outcomes = summary.get("failed_required_outcomes") or []
    command_failures = [
        row for row in outcomes if isinstance(row, dict) and row.get("kind") == "command"
    ]
    if command_failures:
        lines.append("")
        lines.append("Failed required commands:")
        for row in command_failures:
            lines.append(
                f"  - {row.get('status')} {row.get('domain')}.{row.get('command')} "
                f"key={row.get('key')}: {row.get('message')}",
            )
    slots = summary.get("all_slots") or summary.get("test_slots") or []
    if slots:
        lines.append("")
        lines.append("Script slots:")
        for slot in slots:
            if not isinstance(slot, dict):
                continue
            repeat = slot.get("repeat_index")
            repeat_text = f" repeat={repeat}" if repeat is not None else ""
            lines.append(
                f"  - {slot.get('phase')} [{slot.get('overall_result')}]"
                f"{repeat_text} {slot.get('script')}",
            )
    return "\n".join(lines)
