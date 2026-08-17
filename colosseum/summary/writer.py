from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..context import RuntimeContext
from ..results.aggregation import OutcomeRecord, ResultAggregator


def _count_by_kind(
    records: list[OutcomeRecord], *, kind: str, optional: bool
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in records:
        if row.get("kind") != kind:
            continue
        if bool(row.get("optional")) != optional:
            continue
        status = row["status"]
        counts[status] = counts.get(status, 0) + 1
    return counts


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
                if measurement_count is None:
                    measurement_count = ctx.db.count_rows("measurements")
                if command_count is None:
                    command_count = ctx.db.count_rows("commands")
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
            f"Verifications (required): {sum(required_verifications.values())}",
        ]
        for status, count in sorted(required_verifications.items()):
            lines.append(f"  required verification {status}: {count}")
        if required_commands:
            lines.append(f"Commands (required outcomes): {sum(required_commands.values())}")
            for status, count in sorted(required_commands.items()):
                lines.append(f"  required command {status}: {count}")
        if optional_verifications or optional_commands:
            if optional_verifications:
                lines.append(f"Verifications (optional): {sum(optional_verifications.values())}")
                for status, count in sorted(optional_verifications.items()):
                    lines.append(f"  optional verification {status}: {count}")
            if optional_commands:
                lines.append(f"Commands (optional outcomes): {sum(optional_commands.values())}")
                for status, count in sorted(optional_commands.items()):
                    lines.append(f"  optional command {status}: {count}")

        if failed_required:
            lines.append("")
            lines.append("Failed required outcomes:")
            for row in failed_required:
                label = row.get("key") or row.get("command") or "?"
                domain = row.get("domain", "")
                command = row.get("command", "")
                kind = row.get("kind", "outcome")
                lines.append(
                    f"  - [{kind}] {domain}.{command} key={label}: {row.get('message', '')}"
                )

        optional_rows = aggregator.optional_outcomes()
        if optional_rows:
            lines.append("")
            lines.append("Optional outcomes:")
            for row in optional_rows:
                lines.append(
                    f"  - [{row.get('kind')}] {row.get('domain')}.{row.get('command')} "
                    f"key={row.get('key')}: {row['status']}"
                )

        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._write_json(
            output_dir,
            aggregator,
            ctx,
            measurement_count,
            command_count,
            required_verifications,
            optional_verifications,
            required_commands,
            optional_commands,
            failed_required,
        )
        return summary_path

    def _write_json(
        self,
        output_dir: Path,
        aggregator: ResultAggregator,
        ctx: RuntimeContext,
        measurement_count: int,
        command_count: int,
        required_verifications: dict[str, int],
        optional_verifications: dict[str, int],
        required_commands: dict[str, int],
        optional_commands: dict[str, int],
        failed_required: list[OutcomeRecord],
    ) -> None:
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
        json_path = output_dir / "summary.json"
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
