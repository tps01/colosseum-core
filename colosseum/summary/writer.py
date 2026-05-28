from __future__ import annotations

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
        return summary_path
