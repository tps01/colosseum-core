"""GUI run browser helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from colosseum.runner.runtime import (
    RunDirectoryEntry,
    list_run_directory_entries,
    read_summary_json,
)


@dataclass(frozen=True)
class RunBrowserRow:
    entry: RunDirectoryEntry
    status: str
    mtime: float
    children: tuple[RunBrowserRow, ...] = ()


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
        rows.append(
            RunBrowserRow(
                entry=entry,
                status=display_status(summary),
                mtime=mtime,
                children=_suite_child_rows(entry, summary),
            ),
        )
    return RunBrowserSnapshot(rows=rows)


def suite_run_dirs(rows: list[RunBrowserRow]) -> set[Path]:
    """Suite folders that contain case runs and can expand in the browser."""
    found: set[Path] = set()
    for row in rows:
        if row.children:
            found.add(row.entry.path)
        found.update(suite_run_dirs(list(row.children)))
    return found


def _suite_child_rows(
    entry: RunDirectoryEntry,
    summary: dict[str, Any] | None,
) -> tuple[RunBrowserRow, ...]:
    """Case runs stored inside a suite folder, in slot order when the summary has it."""
    found: dict[str, Path] = {}
    try:
        children = list(entry.path.iterdir())
    except OSError:
        return ()
    for child in children:
        if child.is_dir() and (child / "summary.json").is_file():
            found[child.name] = child
    if not found:
        return ()
    ordered: list[Path] = []
    raw_slots: object = []
    if isinstance(summary, dict):
        raw_slots = summary.get("all_slots") or summary.get("test_slots") or []
    if isinstance(raw_slots, list):
        for slot in raw_slots:
            if not isinstance(slot, dict):
                continue
            name = Path(str(slot.get("output_directory") or "")).name
            path = found.pop(name, None)
            if path is not None:
                ordered.append(path)
    ordered.extend(found[name] for name in sorted(found))
    rows: list[RunBrowserRow] = []
    for path in ordered:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        try:
            child_summary = read_summary_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            child_summary = None
        rows.append(
            RunBrowserRow(
                entry=RunDirectoryEntry(path=path, outputs_dir=entry.outputs_dir),
                status=display_status(child_summary),
                mtime=mtime,
            ),
        )
    return tuple(rows)


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


def _append_suite_metrics(lines: list[str], summary: dict[str, Any]) -> None:
    slot_counts = summary.get("test_slot_counts")
    if not isinstance(slot_counts, dict):
        return
    total = slot_counts.get("total", 0)
    passed = slot_counts.get("pass", 0)
    failed = slot_counts.get("fail", 0)
    lines.append(f"Test slots: {total} ({passed} pass, {failed} fail)")
    pass_percent = slot_counts.get("pass_percent")
    fail_percent = slot_counts.get("fail_percent")
    if isinstance(pass_percent, (int, float)) and isinstance(fail_percent, (int, float)):
        lines.append(f"Pass: {pass_percent:.1f}%")
        lines.append(f"Fail: {fail_percent:.1f}%")
    if summary.get("start_time_utc"):
        lines.append(f"Start time: {summary['start_time_utc']}")
    duration = summary.get("duration_seconds")
    if isinstance(duration, (int, float)) and not isinstance(duration, bool):
        lines.append(f"Runtime: {timedelta(seconds=float(duration))}")
    common = summary.get("common_failed_verifications") or []
    if not isinstance(common, list) or not common:
        return
    lines.append("")
    lines.append("Most common failed verifications:")
    for row in common:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"  - {row.get('count')}x test={row.get('test_index')} {row.get('script')} "
            f"{row.get('domain')}.{row.get('command')} key={row.get('key')}",
        )


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
    _append_suite_metrics(lines, summary)
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
    if "fail_fast_stopped" in summary:
        lines.append(
            f"Fail-fast stopped: {'yes' if summary.get('fail_fast_stopped') else 'no'}",
        )
    if summary.get("fail_fast_stop_reason"):
        lines.append(f"Fail-fast reason: {summary.get('fail_fast_stop_reason')}")
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
            cycle = slot.get("cycle_index")
            cycle_text = f" cycle={cycle}" if cycle is not None else ""
            lines.append(
                f"  - {slot.get('phase')} [{slot.get('overall_result')}]"
                f"{repeat_text}{cycle_text} {slot.get('script')}",
            )
    return "\n".join(lines)
