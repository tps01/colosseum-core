from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..context import RuntimeContext
from ..results.aggregation import ResultAggregator


class SummaryWriter:
    def write(self, output_dir: Path, aggregator: ResultAggregator, ctx: RuntimeContext) -> Path:
        summary_path = output_dir / "summary.txt"
        counts = aggregator.counts()
        required = counts.get("required", {})
        optional = counts.get("optional", {})
        failed_required = aggregator.failed_required_verifications()

        measurement_count = 0
        verification_count = counts.get("total", 0)
        if ctx.db.is_initialized():
            measurement_count = ctx.db.count_rows("measurements")

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
            f"Verifications (required): {sum(required.values())}",
        ]
        for status, count in sorted(required.items()):
            lines.append(f"  required {status}: {count}")
        if optional:
            lines.append(f"Verifications (optional): {sum(optional.values())}")
            for status, count in sorted(optional.items()):
                lines.append(f"  optional {status}: {count}")

        if failed_required:
            lines.append("")
            lines.append("Failed required verifications:")
            for row in failed_required:
                label = row.get("key") or row.get("command") or "?"
                domain = row.get("domain", "")
                command = row.get("command", "")
                lines.append(f"  - {domain}.{command} key={label}: {row.get('message', '')}")

        if optional:
            lines.append("")
            lines.append("Optional verifications:")
            for row in aggregator.optional_verifications():
                lines.append(f"  - {row.get('domain')}.{row.get('command')} key={row.get('key')}: {row['status']}")

        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._write_json(output_dir, aggregator, ctx, measurement_count, required, optional, failed_required)
        return summary_path

    def _write_json(
        self,
        output_dir: Path,
        aggregator: ResultAggregator,
        ctx: RuntimeContext,
        measurement_count: int,
        required: dict,
        optional: dict,
        failed_required: list,
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
            "verification_counts": {
                "required": required,
                "optional": optional,
            },
            "failed_required_verifications": [
                {
                    "domain": row.get("domain", ""),
                    "command": row.get("command", ""),
                    "key": row.get("key", ""),
                    "status": row.get("status", ""),
                    "message": row.get("message", ""),
                }
                for row in failed_required
            ],
            "suite_error": aggregator.suite_error,
            "teardown_failed": aggregator.teardown_failed,
        }
        json_path = output_dir / "summary.json"
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
