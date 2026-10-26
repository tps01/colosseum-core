"""Read-only evidence rows for the operator results table."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_FAILURE_STATUSES = frozenset({"FAIL", "ERROR", "BLOCKED"})
_PAGE_SIZE = 40


@dataclass(frozen=True)
class EvidenceRow:
    kind: str
    record_id: int
    status: str
    optional: bool
    step: str
    key: str
    actual: str
    comparison: str
    units: str
    message: str
    domain: str
    command: str
    expected_raw: str
    actual_raw: str
    tolerance_raw: str
    compare_op: str
    artifact_stored: str
    cause: str


@dataclass(frozen=True)
class EvidenceLoad:
    rows: list[EvidenceRow]
    error: str | None = None
    import_origin: str | None = None


def page_size() -> int:
    return _PAGE_SIZE


def load_run_evidence(run_dir: Path) -> EvidenceLoad:
    """Open ``execution.sqlite`` read-only. Never creates or writes the file."""
    database = run_dir / "execution.sqlite"
    if not database.is_file():
        return EvidenceLoad(rows=[], error=f"No execution.sqlite in {run_dir.name}.")
    uri = database.resolve().as_uri() + "?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        return EvidenceLoad(rows=[], error=f"Cannot open execution.sqlite: {exc}")
    try:
        connection.row_factory = sqlite3.Row
        rows = _read_rows(connection)
        origin = _import_origin(connection)
    except sqlite3.Error as exc:
        return EvidenceLoad(rows=[], error=f"Cannot read execution.sqlite: {exc}")
    finally:
        connection.close()
    return EvidenceLoad(rows=rows, import_origin=origin)


def filter_rows(
    rows: list[EvidenceRow],
    *,
    text: str = "",
    status: str = "",
    required_only: bool = False,
    failures_only: bool = False,
) -> list[EvidenceRow]:
    needle = text.strip().casefold()
    wanted = status.strip().upper()
    matched: list[EvidenceRow] = []
    for row in rows:
        if failures_only and not _is_required_failure(row):
            continue
        if required_only and (row.optional or row.kind == "measurement"):
            continue
        if wanted and row.status.upper() != wanted:
            continue
        if needle and needle not in _haystack(row):
            continue
        matched.append(row)
    return matched


def detail_text(row: EvidenceRow, *, units: str) -> str:
    lines = [
        f"Kind: {row.kind}",
        f"Status: {row.status}",
        f"Required: {'no' if row.optional else 'yes'}",
        f"Domain: {row.domain}",
        f"Command: {row.command}",
        f"Step: {row.step or '-'}",
        f"Key: {row.key or '-'}",
        f"Actual: {row.actual or '-'}",
        f"Comparison: {row.comparison or '-'}",
        f"Units: {units or '-'}",
        f"Operator: {row.compare_op or '-'}",
        f"Expected (recorded): {row.expected_raw or '-'}",
        f"Tolerance (recorded): {row.tolerance_raw or '-'}",
        f"Message: {row.message or '-'}",
    ]
    if row.cause:
        lines.append(f"Cause: {row.cause}")
    if row.artifact_stored:
        lines.append(f"Artifact: {row.artifact_stored}")
    return "\n".join(lines)


def units_for(row: EvidenceRow, rows: list[EvidenceRow]) -> str:
    """Units stored on the row, or the single matching measurement. Never guess."""
    if row.units:
        return row.units
    if row.kind == "measurement" or not row.key:
        return ""
    matches = [
        other
        for other in rows
        if other.kind == "measurement"
        and other.domain == row.domain
        and other.command == row.command
        and other.key == row.key
        and other.units
    ]
    if len(matches) == 1:
        return matches[0].units
    return ""


def _is_required_failure(row: EvidenceRow) -> bool:
    return (
        row.kind != "measurement"
        and not row.optional
        and row.status.upper() in _FAILURE_STATUSES
    )


def _haystack(row: EvidenceRow) -> str:
    return " ".join(
        (
            row.kind,
            row.status,
            row.step,
            row.key,
            row.actual,
            row.comparison,
            row.message,
            row.domain,
            row.command,
        ),
    ).casefold()


_VERIFICATION_COLUMNS = (
    "id", "domain", "command", "key", "expected_json", "actual_json", "tolerance_json",
    "compare_op", "status", "optional", "message", "description",
)
_COMMAND_COLUMNS = (
    "id", "domain", "command", "key", "result_json", "status", "optional", "message", "cause",
)
_MEASUREMENT_COLUMNS = (
    "id", "domain", "command", "key", "value_json", "units", "artifact_path", "status",
)


def _read_rows(connection: sqlite3.Connection) -> list[EvidenceRow]:
    """Read result tables, skipping columns that older databases never stored."""
    verifications = _fetch_table(connection, "verifications", _VERIFICATION_COLUMNS)
    commands = _fetch_table(connection, "commands", _COMMAND_COLUMNS)
    measurements = _fetch_table(connection, "measurements", _MEASUREMENT_COLUMNS)
    if verifications is None and commands is None and measurements is None:
        raise sqlite3.OperationalError("execution.sqlite has no result tables")
    rows: list[EvidenceRow] = []
    for item in verifications or []:
        expected = _cell(item, "expected_json")
        actual = _cell(item, "actual_json")
        tolerance = _cell(item, "tolerance_json")
        op = _cell(item, "compare_op")
        rows.append(
            EvidenceRow(
                kind="verification",
                record_id=int(item["id"]),
                status=_cell(item, "status"),
                optional=_flag(item, "optional"),
                step=_cell(item, "description") or _cell(item, "key"),
                key=_cell(item, "key"),
                actual=_display_json(actual),
                comparison=comparison_label(op, expected, tolerance),
                units="",
                message=_cell(item, "message"),
                domain=_cell(item, "domain"),
                command=_cell(item, "command"),
                expected_raw=expected,
                actual_raw=actual,
                tolerance_raw=tolerance,
                compare_op=op,
                artifact_stored="",
                cause="",
            ),
        )
    for item in commands or []:
        result = _cell(item, "result_json")
        rows.append(
            EvidenceRow(
                kind="command",
                record_id=int(item["id"]),
                status=_cell(item, "status"),
                optional=_flag(item, "optional"),
                step=_cell(item, "key") or _cell(item, "command"),
                key=_cell(item, "key"),
                actual=_display_json(result),
                comparison="",
                units="",
                message=_cell(item, "message"),
                domain=_cell(item, "domain"),
                command=_cell(item, "command"),
                expected_raw="",
                actual_raw=result,
                tolerance_raw="",
                compare_op="",
                artifact_stored="",
                cause=_cell(item, "cause"),
            ),
        )
    for item in measurements or []:
        value = _cell(item, "value_json")
        rows.append(
            EvidenceRow(
                kind="measurement",
                record_id=int(item["id"]),
                status=_cell(item, "status"),
                optional=False,
                step=_cell(item, "key"),
                key=_cell(item, "key"),
                actual=_display_json(value),
                comparison="",
                units=_cell(item, "units"),
                message="",
                domain=_cell(item, "domain"),
                command=_cell(item, "command"),
                expected_raw="",
                actual_raw=value,
                tolerance_raw="",
                compare_op="",
                artifact_stored=_cell(item, "artifact_path"),
                cause="",
            ),
        )
    return rows


def _fetch_table(
    connection: sqlite3.Connection,
    table: str,
    wanted: tuple[str, ...],
) -> list[sqlite3.Row] | None:
    """Return rows, or None when the table itself is absent."""
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    if exists is None:
        return None
    present_columns = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}
    selected = [name for name in wanted if name in present_columns]
    if "id" not in selected:
        raise sqlite3.OperationalError(f"{table} has no id column")
    # Callers pass fixed table names; selected columns come from that table's pragma.
    sql = f"SELECT {', '.join(selected)} FROM {table} ORDER BY id ASC"  # nosec B608
    return list(connection.execute(sql))


def _cell(item: sqlite3.Row, column: str) -> str:
    if column not in _names(item):
        return ""
    return _text(item[column])


def _flag(item: sqlite3.Row, column: str) -> bool:
    if column not in _names(item):
        return False
    return bool(item[column])


def _names(item: sqlite3.Row) -> set[str]:
    # Iterating a Row yields values, so the column names come from keys().
    return {str(name) for name in item.keys()}  # noqa: SIM118


def _import_origin(connection: sqlite3.Connection) -> str | None:
    try:
        found = connection.execute(
            "SELECT value FROM run_metadata WHERE key = 'imported_from'",
        ).fetchone()
    except sqlite3.Error:
        return None
    if found is None:
        return None
    value = _text(found["value"])
    return value or None


def comparison_label(compare_op: str, expected: str, tolerance: str) -> str:
    """Format the recorded comparison. One-sided bounds are not shown as ±."""
    op = compare_op.upper()
    expected_value = _parse_json(expected)
    tolerance_value = _parse_json(tolerance)
    if op == "EQ":
        return f"== {_plain(expected_value)}"
    if op == "GE":
        return f">= {_plain(expected_value)}"
    if op == "LE":
        return f"<= {_plain(expected_value)}"
    if op == "GELE" and _is_number(expected_value):
        if isinstance(tolerance_value, str):
            text = tolerance_value.strip()
            if text.startswith(("+", "-")) and len(text) > 1:
                return f"{_plain(expected_value)} {text}"
        if _is_number(tolerance_value):
            return f"{_plain(expected_value)} ± {_plain(tolerance_value)}"
    if op:
        return f"{op} {_plain(expected_value)}".strip()
    return ""


def _parse_json(text: str) -> object:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _display_json(text: str) -> str:
    parsed = _parse_json(text)
    if parsed is None:
        return ""
    return _plain(parsed)


def _plain(value: object) -> str:
    if isinstance(value, float):
        return format(value, ".12g")
    return str(value)


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
