from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path

    from colosseum.context import RuntimeContext
    from colosseum.results.aggregation import OutcomeRecord, ResultAggregator
    from colosseum.runner.runtime import SuiteSlotResult


def _count_by_kind(
    records: list[OutcomeRecord], *, kind: str, optional: bool,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in records:
        if row.get("kind") != kind or bool(row.get("optional")) != optional:
            continue
        status = row["status"]
        counts[status] = counts.get(status, 0) + 1
    return counts


def _outcome_lines(rows: list[OutcomeRecord], *, header: str) -> list[str]:
    if not rows:
        return []
    lines = ["", header]
    for row in rows:
        if header.startswith("Failed"):
            label = row.get("key") or row.get("command") or "?"
            lines.append(
                f"  - [{row.get('kind', 'outcome')}] {row.get('domain', '')}."
                f"{row.get('command', '')} key={label}: {row.get('message', '')}",
            )
        else:
            lines.append(
                f"  - [{row.get('kind')}] {row.get('domain')}.{row.get('command')} "
                f"key={row.get('key')}: {row['status']}",
            )
    return lines


def _count_lines(label: str, prefix: str, counts: dict[str, int]) -> list[str]:
    if not counts:
        return []
    lines = [f"{label}: {sum(counts.values())}"]
    lines.extend(f"  {prefix} {status}: {count}" for status, count in sorted(counts.items()))
    return lines


def _slot_dict(slot: SuiteSlotResult) -> dict[str, object]:
    return {
        "phase": slot.phase,
        "script": str(slot.script_path),
        "output_directory": str(slot.output_dir),
        "test_index": slot.test_index,
        "repeat_index": slot.repeat_index,
        "cycle_index": slot.cycle_index,
        "overall_result": slot.overall,
        "exit_code": slot.exit_code,
    }


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _test_slot_counts(slots: list[SuiteSlotResult]) -> dict[str, int | float]:
    total = len(slots)
    passed = sum(1 for slot in slots if slot.overall == "PASS")
    failed = total - passed
    counts: dict[str, int | float] = {"total": total, "pass": passed, "fail": failed}
    if total > 0:
        counts["pass_percent"] = round(100.0 * passed / total, 1)
        counts["fail_percent"] = round(100.0 * failed / total, 1)
    return counts


def _slot_count_lines(counts: dict[str, int | float]) -> list[str]:
    total = int(counts["total"])
    lines = [
        f"Test slots: {total} ({int(counts['pass'])} pass, {int(counts['fail'])} fail)",
    ]
    if total > 0:
        lines.append(f"Pass: {counts['pass_percent']:.1f}%")
        lines.append(f"Fail: {counts['fail_percent']:.1f}%")
    return lines


def _failed_verification_rows(slot: SuiteSlotResult) -> list[dict[str, object]]:
    summary_path = slot.output_dir / "summary.json"
    if not summary_path.is_file():
        return []
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []
    rows = payload.get("failed_required_verifications")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _slot_failure_identities(slot: SuiteSlotResult) -> set[tuple[str, str, str]]:
    found: set[tuple[str, str, str]] = set()
    for row in _failed_verification_rows(slot):
        found.add((
            _text(row.get("domain")),
            _text(row.get("command")),
            _text(row.get("key")),
        ))
    return found


def _repeated_test_indexes(slots: list[SuiteSlotResult]) -> set[int]:
    counts: dict[int, int] = {}
    for slot in slots:
        if slot.test_index is None:
            continue
        counts[slot.test_index] = counts.get(slot.test_index, 0) + 1
    return {index for index, count in counts.items() if count > 1}


def _failure_rank_key(
    item: tuple[tuple[int, str, str, str, str], int],
) -> tuple[int, str, str, str, str, int]:
    identity, count = item
    test_index, script, domain, command, key = identity
    return (-count, script, domain, command, key, test_index)


def _common_failed_verifications(
    slots: list[SuiteSlotResult],
) -> list[dict[str, int | str]]:
    repeated = _repeated_test_indexes(slots)
    totals: dict[tuple[int, str, str, str, str], int] = {}
    for slot in slots:
        test_index = slot.test_index
        if not isinstance(test_index, int) or test_index not in repeated:
            continue
        script = slot.script_path.name
        for domain, command, key in _slot_failure_identities(slot):
            identity = (test_index, script, domain, command, key)
            totals[identity] = totals.get(identity, 0) + 1
    ranked = sorted(totals.items(), key=_failure_rank_key)
    return [
        {
            "count": count,
            "test_index": test_index,
            "script": script,
            "domain": domain,
            "command": command,
            "key": key,
        }
        for (test_index, script, domain, command, key), count in ranked[:10]
    ]


def _common_failure_lines(rows: list[dict[str, int | str]]) -> list[str]:
    if not rows:
        return []
    lines = ["", "Most common failed verifications:"]
    for row in rows:
        lines.append(
            f"  - {row['count']}x test={row['test_index']} {row['script']} "
            f"{row['domain']}.{row['command']} key={row['key']}",
        )
    return lines


class SummaryWriter:
    def write(
        self,
        output_dir: Path,
        aggregator: ResultAggregator,
        ctx: RuntimeContext,
        *,
        measurement_count: int | None = None,
        command_count: int | None = None,
    ) -> Path:
        summary_path = output_dir / "summary.txt"
        records = aggregator._records  # noqa: SLF001 — summary formatting
        required_verifications = _count_by_kind(records, kind="verification", optional=False)
        optional_verifications = _count_by_kind(records, kind="verification", optional=True)
        required_commands = _count_by_kind(records, kind="command", optional=False)
        optional_commands = _count_by_kind(records, kind="command", optional=True)
        failed_required = aggregator.failed_required_outcomes()

        if measurement_count is None or command_count is None:
            if ctx.db.is_initialized():
                measurement_count = measurement_count or ctx.db.count_rows("measurements")
                command_count = command_count or ctx.db.count_rows("commands")
            else:
                measurement_count = measurement_count or 0
                command_count = command_count or 0

        lines = [
            "Colosseum Run Summary",
            "====================",
            f"Colosseum version: {ctx.framework_version}",
            f"Test case: {ctx.test_case_name}",
            f"Suite: {ctx.suite_name or 'N/A'}",
            f"Config file: {ctx.config_path or 'N/A'}",
            f"Output directory: {output_dir}",
            f"End time: {datetime.now(timezone.utc).isoformat()}",
            f"Overall result: {'PASS' if aggregator.overall_pass() else 'FAIL'}",
            f"Exit code: {aggregator.exit_code()}",
            "",
            f"Measurements: {measurement_count}",
            f"Commands: {command_count}",
            *_count_lines(
                "Verifications (required)", "required verification", required_verifications,
            ),
            *_count_lines(
                "Commands (required outcomes)", "required command", required_commands,
            ),
            *_count_lines(
                "Verifications (optional)", "optional verification", optional_verifications,
            ),
            *_count_lines(
                "Commands (optional outcomes)", "optional command", optional_commands,
            ),
            *_outcome_lines(failed_required, header="Failed required outcomes:"),
            *_outcome_lines(aggregator.optional_outcomes(), header="Optional outcomes:"),
        ]
        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        payload = {
            "colosseum_version": ctx.framework_version,
            "test_case": ctx.test_case_name,
            "suite": ctx.suite_name,
            "config_path": str(ctx.config_path) if ctx.config_path else None,
            "output_directory": str(output_dir),
            "end_time_utc": datetime.now(timezone.utc).isoformat(),
            "overall_result": "PASS" if aggregator.overall_pass() else "FAIL",
            "exit_code": aggregator.exit_code(),
            "measurement_count": measurement_count,
            "command_count": command_count,
            "verification_counts": {
                "required": required_verifications,
                "optional": optional_verifications,
            },
            "command_counts": {
                "required": required_commands,
                "optional": optional_commands,
            },
            "failed_required_outcomes": [
                {
                    "kind": row.get("kind", ""),
                    "domain": row.get("domain", ""),
                    "command": row.get("command", ""),
                    "key": row.get("key", ""),
                    "status": row.get("status", ""),
                    "message": row.get("message", ""),
                }
                for row in failed_required
            ],
            "failed_required_verifications": [
                {
                    "domain": row.get("domain", ""),
                    "command": row.get("command", ""),
                    "key": row.get("key", ""),
                    "status": row.get("status", ""),
                    "message": row.get("message", ""),
                }
                for row in failed_required
                if row.get("kind") == "verification"
            ],
            "suite_error": aggregator.suite_error,
            "teardown_failed": aggregator.teardown_failed,
        }
        (output_dir / "summary.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        return summary_path


class SuiteSummaryWriter:
    def write(
        self,
        container_dir: Path,
        ctx: RuntimeContext,
        *,
        exit_code: int,
        overall: str,
    ) -> Path:
        summary_path = container_dir / "summary.txt"
        ended_at = datetime.now(timezone.utc)
        started = ctx.suite_started_at
        started_utc = started.astimezone(timezone.utc) if started is not None else None
        test_slots = cast("list[SuiteSlotResult]", ctx.suite_test_results)
        slot_counts = _test_slot_counts(test_slots)
        common_failures = _common_failed_verifications(test_slots)
        lines = [
            "Colosseum Suite Summary",
            "=======================",
            f"Colosseum version: {ctx.framework_version}",
            f"Suite: {ctx.suite_name or ctx.test_case_name}",
            f"Config file: {ctx.config_path or 'N/A'}",
            f"Output directory: {container_dir}",
            f"End time: {ended_at.isoformat()}",
        ]
        if started_utc is not None:
            lines.append(f"Start time: {started_utc.isoformat()}")
            lines.append(f"Runtime: {ended_at - started_utc}")
        lines.extend(_slot_count_lines(slot_counts))
        lines.extend([
            f"Overall result: {overall}",
            f"Exit code: {exit_code}",
            f"Suite failed: {'yes' if ctx.session.suite_failed else 'no'}",
            f"Fail-fast stopped: {'yes' if ctx.session.fail_fast_stopped else 'no'}",
            "",
            "Test slots (determine suite pass/fail):",
        ])
        if not test_slots:
            lines.append("  (none)")
        for slot in test_slots:
            repeat = f" repeat={slot.repeat_index}" if slot.repeat_index is not None else ""
            cycle = f" cycle={slot.cycle_index}" if slot.cycle_index is not None else ""
            lines.append(
                f"  - [{slot.overall}] test={slot.test_index}{repeat}{cycle} "
                f"{slot.script_path.name} -> {slot.output_dir.name}",
            )
        lines.extend(_common_failure_lines(common_failures))
        lines.extend(["", "All script slots:"])
        if not ctx.suite_slot_results:
            lines.append("  (none)")
        for slot in ctx.suite_slot_results:
            result = slot.overall or "n/a"
            lines.append(
                f"  - {slot.phase}: {slot.script_path.name} ({result}) -> {slot.output_dir.name}",
            )
        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        payload: dict[str, object] = {
            "colosseum_version": ctx.framework_version,
            "suite": ctx.suite_name,
            "config_path": str(ctx.config_path) if ctx.config_path else None,
            "output_directory": str(container_dir),
            "end_time_utc": ended_at.isoformat(),
            "overall_result": overall,
            "exit_code": exit_code,
            "suite_failed": ctx.session.suite_failed,
            "suite_fail_reason": ctx.session.suite_fail_reason,
            "fail_fast_stopped": ctx.session.fail_fast_stopped,
            "fail_fast_stop_reason": ctx.session.fail_fast_stop_reason,
            "fail_fast_stop_script": ctx.session.fail_fast_stop_script,
            "test_slots": [_slot_dict(slot) for slot in test_slots],
            "all_slots": [_slot_dict(slot) for slot in ctx.suite_slot_results],
            "test_slot_counts": slot_counts,
            "common_failed_verifications": common_failures,
        }
        if started_utc is not None:
            payload["start_time_utc"] = started_utc.isoformat()
            payload["duration_seconds"] = (ended_at - started_utc).total_seconds()
        (container_dir / "summary.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        return summary_path

    @staticmethod
    def suite_exit_code(ctx: RuntimeContext) -> int:
        if ctx.session.suite_failed:
            return 1
        if not ctx.suite_test_results:
            return 0
        if any(slot.exit_code != 0 for slot in ctx.suite_test_results):
            return 1
        return 0
