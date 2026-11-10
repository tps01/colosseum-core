"""Format finalized requirement verdicts for text and stdout reports."""

from __future__ import annotations

from typing import Any


def requirement_lines(rows: list[dict[str, Any]], *, suite: bool = False) -> list[str]:
    """Format requirement rows for ``summary.txt`` / INFO logs."""
    if not rows:
        return []
    lines = ["", "Requirements:"]
    for row in rows:
        req_id = row.get("id", "")
        status = row.get("status", "?")
        fail_rows = row.get("failures") or []
        if not fail_rows:
            lines.append(f"  {req_id}: {status}")
            continue
        if suite:
            details: list[str] = []
            for fail in fail_rows:
                if not isinstance(fail, dict):
                    continue
                test_index = fail.get("test_index")
                script = fail.get("script") or ""
                domain = fail.get("domain") or ""
                command = fail.get("command") or ""
                key = fail.get("key") or ""
                details.append(
                    f"test={test_index} {script} {domain}.{command} key={key}",
                )
            detail = "; ".join(details)
            lines.append(f"  {req_id}: {status} ({detail})")
        else:
            details = []
            for fail in fail_rows:
                if not isinstance(fail, dict):
                    continue
                details.append(
                    f"{fail.get('domain', '')}.{fail.get('command', '')} key={fail.get('key', '')}",
                )
            detail = "; ".join(details)
            lines.append(f"  {req_id}: {status} ({detail})")
    return lines
