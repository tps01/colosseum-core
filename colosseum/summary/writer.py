from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

from colosseum.database import DatabaseManager
from colosseum.results.aggregation import build_run_summary, build_suite_summary
from colosseum.summary.requirements import requirement_lines

if TYPE_CHECKING:
    from pathlib import Path

    from colosseum.context import RuntimeContext
    from colosseum.results.aggregation import OutcomeRecord, ResultAggregator
    from colosseum.runner.runtime import SuiteSlotResult


def _description_prefix(row: OutcomeRecord) -> str:
    if row.get("kind") != "verification":
        return ""
    text = row.get("description") or ""
    if not isinstance(text, str):
        text = str(text)
    text = text.strip()
    return f"{text} " if text else ""


def _dry_run_lines(records: list[OutcomeRecord], tips: list[str] | None = None) -> list[str]:
    lines = ["", "Dry run calls:"]
    if not records:
        lines.append("  (none)")
    else:
        for row in records:
            lines.append(
                f"  - [{row.get('kind', 'outcome')}] {row.get('domain', '')}."
                f"{row.get('command', '')} key={row.get('key', '')}: {row.get('status', '')}",
            )
    if tips:
        lines.extend(["", "Dry-run tips:"])
        lines.extend(f"  - {tip}" for tip in tips)
    return lines


def _outcome_lines(rows: list[OutcomeRecord], *, header: str) -> list[str]:
    if not rows:
        return []
    lines = ["", header]
    for row in rows:
        label = _description_prefix(row)
        if header.startswith("Failed"):
            key = row.get("key") or row.get("command") or "?"
            lines.append(
                f"  - [{row.get('kind', 'outcome')}] {label}{row.get('domain', '')}."
                f"{row.get('command', '')} key={key}: {row.get('message', '')}",
            )
        else:
            lines.append(
                f"  - [{row.get('kind')}] {label}{row.get('domain')}.{row.get('command')} "
                f"key={row.get('key')}: {row['status']}",
            )
    return lines


def _count_lines(label: str, prefix: str, counts: dict[str, int]) -> list[str]:
    if not counts:
        return []
    lines = [f"{label}: {sum(counts.values())}"]
    lines.extend(f"  {prefix} {status}: {count}" for status, count in sorted(counts.items()))
    return lines


def _input_file_lines(slot: SuiteSlotResult) -> list[str]:
    return [
        f"      config: {slot.config_path or 'N/A'}",
        f"      parameters: {slot.parameters_path or 'N/A'}",
        f"      metadata: {slot.metadata_path or 'N/A'}",
    ]


def _slot_count_lines(counts: dict[str, int | float]) -> list[str]:
    total = int(counts["total"])
    lines = [
        f"Test slots: {total} ({int(counts['pass'])} pass, {int(counts['fail'])} fail)",
    ]
    if total > 0:
        lines.append(f"Pass: {counts['pass_percent']:.1f}%")
        lines.append(f"Fail: {counts['fail_percent']:.1f}%")
    return lines


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
        payload: dict[str, Any] | None = None,
    ) -> Path:
        summary_path = output_dir / "summary.txt"
        if payload is None:
            payload = build_run_summary(
                ctx,
                aggregator,
                measurement_count=measurement_count
                if measurement_count is not None
                else (ctx.db.count_rows("measurements") if ctx.db.is_initialized() else 0),
                command_count=command_count
                if command_count is not None
                else (ctx.db.count_rows("commands") if ctx.db.is_initialized() else 0),
            )
        records = payload["outcomes"]
        required_verifications = payload["verification_counts"]["required"]
        optional_verifications = payload["verification_counts"]["optional"]
        required_commands = payload["command_counts"]["required"]
        optional_commands = payload["command_counts"]["optional"]
        failed_required = [
            row
            for row in records
            if not row["optional"] and row["status"] in {"FAIL", "ERROR", "BLOCKED"}
        ]
        measurement_count = payload["measurement_count"]
        command_count = payload["command_count"]
        lines = [
            "Colosseum Run Summary",
            "====================",
            f"Colosseum version: {payload['colosseum_version']}",
            f"Test case: {payload['test_case']}",
            f"Suite: {payload['suite'] or 'N/A'}",
            f"Config file: {payload['config_path'] or 'N/A'}",
            f"Parameters file: {payload['parameters_path'] or 'N/A'}",
            f"Metadata file: {payload['metadata_path'] or 'N/A'}",
            f"Output directory: {output_dir}",
            f"End time: {payload['end_time_utc']}",
            f"Overall result: {payload['overall_result']}",
            f"Exit code: {payload['exit_code']}",
            *(["Dry run: yes"] if payload.get("dry_run") else []),
            "",
            f"Measurements: {measurement_count}",
            f"Commands: {command_count}",
            *_count_lines(
                "Verifications (required)",
                "required verification",
                required_verifications,
            ),
            *_count_lines(
                "Commands (required outcomes)",
                "required command",
                required_commands,
            ),
            *_count_lines(
                "Verifications (optional)",
                "optional verification",
                optional_verifications,
            ),
            *_count_lines(
                "Commands (optional outcomes)",
                "optional command",
                optional_commands,
            ),
            *(
                _dry_run_lines(records, tips=payload.get("dry_run_tips"))
                if payload.get("dry_run")
                else []
            ),
            *_outcome_lines(failed_required, header="Failed required outcomes:"),
            *_outcome_lines(payload["optional_outcomes"], header="Optional outcomes:"),
            *requirement_lines(payload["requirements"]),
        ]
        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        public = {
            key: value
            for key, value in payload.items()
            if key not in {"outcomes", "optional_outcomes", "stored_status"}
        }
        (output_dir / "summary.json").write_text(
            json.dumps(public, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
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
        payload: dict[str, Any] | None = None,
    ) -> Path:
        summary_path = container_dir / "summary.txt"
        if payload is None:
            payload = build_suite_summary(ctx, exit_code=exit_code, overall=overall)
        ended_at = datetime.fromisoformat(payload["end_time_utc"])
        started_utc = (
            datetime.fromisoformat(payload["start_time_utc"])
            if "start_time_utc" in payload
            else None
        )
        test_slots = ctx.suite_test_results
        slot_counts = payload["test_slot_counts"]
        common_failures = payload["common_failed_verifications"]
        requirement_rows = payload["requirements"]
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
        lines.extend(
            [
                f"Overall result: {overall}",
                f"Exit code: {exit_code}",
                f"Fail-fast stopped: {'yes' if ctx.session.fail_fast_stopped else 'no'}",
            ],
        )
        if ctx.session.fail_fast_stop_reason:
            lines.append(f"Fail-fast reason: {ctx.session.fail_fast_stop_reason}")
        lines.extend(
            [
                "",
                "Test slots (determine suite pass/fail):",
            ],
        )
        if not test_slots:
            lines.append("  (none)")
        for slot in test_slots:
            repeat = f" repeat={slot.repeat_index}" if slot.repeat_index is not None else ""
            cycle = f" cycle={slot.cycle_index}" if slot.cycle_index is not None else ""
            lines.append(
                f"  - [{slot.overall}] test={slot.test_index}{repeat}{cycle} "
                f"{slot.script_path.name} -> {slot.output_dir.name}",
            )
            lines.extend(_input_file_lines(slot))
        lines.extend(_common_failure_lines(common_failures))
        lines.extend(requirement_lines(requirement_rows, suite=True))
        lines.extend(["", "All script slots:"])
        if not ctx.suite_slot_results:
            lines.append("  (none)")
        for slot in ctx.suite_slot_results:
            result = slot.overall or "n/a"
            lines.append(
                f"  - {slot.phase}: {slot.script_path.name} ({result}) -> {slot.output_dir.name}",
            )
            lines.extend(_input_file_lines(slot))
        payload["output_directory"] = str(container_dir)
        if (container_dir / "execution.sqlite").is_file():
            DatabaseManager.persist_results(
                container_dir / "execution.sqlite",
                payload,
                kind="suite",
                slots=[slot.persisted(container_dir) for slot in ctx.suite_slot_results],
            )
        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        (container_dir / "summary.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
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
