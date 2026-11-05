"""Aggregate verification ``requirements=`` ids for summary and stdout reports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from colosseum.results.aggregation import OutcomeRecord
    from colosseum.runner.runtime import SuiteSlotResult

_PASSING = frozenset({"PASS", "DRY"})


def coerce_requirements(value: object) -> list[str]:
    """Return requirement ids from a string or list of strings.

    A string is split on commas. A list keeps each stripped item (not split again).
    Empty tokens are dropped. Raises ``TypeError`` for other types.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        ids: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise TypeError(
                    "requirements list items must be strings, "
                    f"got {type(item).__name__}",
                )
            text = item.strip()
            if text:
                ids.append(text)
        return ids
    raise TypeError(
        "requirements must be a string or list of strings, "
        f"got {type(value).__name__}",
    )


def _identity(row: OutcomeRecord) -> dict[str, str]:
    return {
        "domain": str(row.get("domain") or ""),
        "command": str(row.get("command") or ""),
        "key": str(row.get("key") or ""),
    }


def aggregate_requirements(records: list[OutcomeRecord]) -> list[dict[str, Any]]:
    """Build first-seen requirement rows from verification outcomes."""
    order: list[str] = []
    failures: dict[str, list[dict[str, str]]] = {}
    seen: set[str] = set()
    for row in records:
        if row.get("kind") != "verification":
            continue
        ids = row.get("requirements") or []
        if not isinstance(ids, list) or not ids:
            continue
        for req_id in ids:
            if not isinstance(req_id, str) or not req_id:
                continue
            if req_id not in seen:
                seen.add(req_id)
                order.append(req_id)
                failures[req_id] = []
            if row.get("status") not in _PASSING:
                failures[req_id].append(_identity(row))
    return [
        {
            "id": req_id,
            "status": "PASS" if not failures[req_id] else "FAIL",
            "failures": failures[req_id],
        }
        for req_id in order
    ]


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
                    f"{fail.get('domain', '')}.{fail.get('command', '')} "
                    f"key={fail.get('key', '')}",
                )
            detail = "; ".join(details)
            lines.append(f"  {req_id}: {status} ({detail})")
    return lines


def _slot_requirement_rows(slot: SuiteSlotResult) -> list[dict[str, Any]]:
    import json

    summary_path = slot.output_dir / "summary.json"
    if not summary_path.is_file():
        return []
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []
    rows = payload.get("requirements")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def rollup_suite_requirements(slots: list[SuiteSlotResult]) -> list[dict[str, Any]]:
    """Roll requirement ids across test slots that reported them."""
    order: list[str] = []
    failures: dict[str, list[dict[str, Any]]] = {}
    seen: set[str] = set()
    for slot in slots:
        script = slot.script_path.name if slot.script_path is not None else ""
        for row in _slot_requirement_rows(slot):
            req_id = row.get("id")
            if not isinstance(req_id, str) or not req_id:
                continue
            if req_id not in seen:
                seen.add(req_id)
                order.append(req_id)
                failures[req_id] = []
            if row.get("status") == "PASS":
                continue
            for fail in row.get("failures") or []:
                if not isinstance(fail, dict):
                    continue
                failures[req_id].append(
                    {
                        "test_index": slot.test_index,
                        "script": script,
                        "domain": str(fail.get("domain") or ""),
                        "command": str(fail.get("command") or ""),
                        "key": str(fail.get("key") or ""),
                    },
                )
            if not (row.get("failures") or []):
                failures[req_id].append(
                    {
                        "test_index": slot.test_index,
                        "script": script,
                        "domain": "",
                        "command": "",
                        "key": "",
                    },
                )
    return [
        {
            "id": req_id,
            "status": "PASS" if not failures[req_id] else "FAIL",
            "failures": failures[req_id],
        }
        for req_id in order
    ]
