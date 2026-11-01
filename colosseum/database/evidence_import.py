"""Import measurements and commands from a prior run directory."""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from colosseum.database import CommandRow, MeasurementRow
from colosseum.database.artifact_paths import relativize_imported_artifact

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from colosseum.context import RuntimeContext

_MEASUREMENT_COLUMNS = (
    "domain",
    "command",
    "key",
    "row_index",
    "value_json",
    "units",
    "artifact_path",
    "status",
    "timestamp",
)
_COMMAND_COLUMNS = (
    "domain",
    "command",
    "key",
    "result_json",
    "status",
    "optional",
    "message",
    "timestamp",
)
_MEASUREMENT_SELECT = (
    "SELECT domain, command, key, row_index, value_json, units, artifact_path, "
    "status, timestamp FROM measurements ORDER BY id ASC"
)
_COMMAND_SELECT = (
    "SELECT domain, command, key, result_json, status, optional, message, timestamp "
    "FROM commands ORDER BY id ASC"
)


def resolve_previous_run_dir(path: Path) -> Path:
    """Resolve a prior run directory, accepting optional ``-pass`` / ``-fail`` suffix."""
    from colosseum.paths import absolute_path

    resolved = absolute_path(path)
    if resolved.is_dir():
        return resolved
    raise FileNotFoundError(f"Previous output directory not found: {resolved}")


def resolve_previous_db(path: Path) -> Path:
    run_dir = resolve_previous_run_dir(path)
    db_path = run_dir / "execution.sqlite"
    if not db_path.is_file():
        raise FileNotFoundError(f"execution.sqlite not found in {run_dir}")
    return db_path


def import_evidence_from_previous(ctx: object, previous_dir: Path) -> None:
    """Copy measurements and commands from a prior run into the active database."""
    from colosseum.context import RuntimeContext

    if not isinstance(ctx, RuntimeContext):
        raise TypeError("ctx must be a RuntimeContext")
    if not ctx.db.is_initialized():
        raise RuntimeError("Database must be initialized before importing evidence")

    source_db = resolve_previous_db(previous_dir)
    source = sqlite3.connect(str(source_db))
    try:
        source_run = source_db.parent
        _copy_table_rows(
            source,
            ctx,
            _MEASUREMENT_SELECT,
            _MEASUREMENT_COLUMNS,
            lambda runtime, row: _insert_measurement_row(runtime, row, source_run),
        )
        _copy_table_rows(
            source,
            ctx,
            _COMMAND_SELECT,
            _COMMAND_COLUMNS,
            _insert_command_row,
        )
    finally:
        source.close()

    ctx.db.insert_run_metadata("imported_from", str(source_db.parent))


def _copy_table_rows(
    source: sqlite3.Connection,
    ctx: RuntimeContext,
    select_sql: str,
    columns: tuple[str, ...],
    inserter: Callable[[RuntimeContext, dict[str, object]], None],
) -> None:
    rows = source.execute(select_sql).fetchall()
    for row in rows:
        if len(row) != len(columns):
            raise ValueError(f"row length {len(row)} != column count {len(columns)}")
        inserter(ctx, dict(zip(columns, row)))


def _insert_measurement_row(
    ctx: RuntimeContext,
    row: dict[str, object],
    source_run: Path,
) -> None:
    raw_artifact = row["artifact_path"]
    artifact = relativize_imported_artifact(
        None if raw_artifact is None else str(raw_artifact),
        source_run,
    )
    ctx.db.insert_measurement(
        MeasurementRow(
            domain=str(row["domain"]),
            command=str(row["command"]),
            key=str(row["key"]),
            row_index=int(row["row_index"]),  # type: ignore[call-overload]
            value=_loads_json_value(row["value_json"]),
            units=row["units"],  # type: ignore[arg-type]
            artifact_path=artifact,
            status=str(row["status"]),
            timestamp=str(row["timestamp"]),
        ),
    )


def _insert_command_row(ctx: RuntimeContext, row: dict[str, object]) -> None:
    ctx.db.insert_command(
        CommandRow(
            domain=str(row["domain"]),
            command=str(row["command"]),
            key=str(row["key"]),
            result=_loads_json_value(row["result_json"]),
            status=str(row["status"]),
            optional=bool(row["optional"]),
            message=str(row["message"] or ""),
            timestamp=str(row["timestamp"]),
        ),
    )


def _loads_json_value(value: object) -> object | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes, bytearray)):
        return json.loads(value)  # type: ignore[no-any-return]
    raise TypeError(f"unexpected JSON column value: {type(value)!r}")
