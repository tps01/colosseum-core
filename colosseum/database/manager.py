from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from colosseum.context import RuntimeContext
from .schema import SCHEMA_SQL
from .write_queue import DatabaseWriteQueue, WriteJob

_TABLE_SELECT_SQL = {
    "run_metadata": "SELECT * FROM run_metadata",
    "measurements": "SELECT * FROM measurements",
    "verifications": "SELECT * FROM verifications",
    "events": "SELECT * FROM events",
    "commands": "SELECT * FROM commands",
    "provenance": "SELECT * FROM provenance",
}
_TABLE_COUNT_SQL = {
    "run_metadata": "SELECT COUNT(*) FROM run_metadata",
    "measurements": "SELECT COUNT(*) FROM measurements",
    "verifications": "SELECT COUNT(*) FROM verifications",
    "events": "SELECT COUNT(*) FROM events",
    "commands": "SELECT COUNT(*) FROM commands",
    "provenance": "SELECT COUNT(*) FROM provenance",
}
_TABLE_COUNT_KEY_SQL = {
    "run_metadata": "SELECT COUNT(*) FROM run_metadata WHERE key = ?",
    "measurements": "SELECT COUNT(*) FROM measurements WHERE key = ?",
    "verifications": "SELECT COUNT(*) FROM verifications WHERE key = ?",
    "events": "SELECT COUNT(*) FROM events WHERE key = ?",
    "commands": "SELECT COUNT(*) FROM commands WHERE key = ?",
}


@dataclass
class MeasurementRow:
    """Measurement write/read row. ``id`` is set when loaded from SQLite."""

    domain: str
    command: str
    key: str
    row_index: int = 0
    value: Any = None
    units: str | None = None
    artifact_path: str | None = None
    status: str = "PASS"
    timestamp: str = ""
    id: int | None = None


@dataclass
class VerificationRow:
    """Verification write/read row. ``id`` is set when loaded from SQLite."""

    domain: str
    command: str
    key: str
    expected: Any = None
    actual: Any = None
    tolerance: float | None = None
    compare_op: str | None = None
    status: str = "PASS"
    optional: bool = False
    message: str | None = ""
    description: str | None = None
    timestamp: str = ""
    id: int | None = None


@dataclass
class CommandRow:
    domain: str
    command: str
    key: str = ""
    result: Any = None
    status: str = "PASS"
    optional: bool = False
    message: str = ""
    cause: str = ""
    timestamp: str = ""
    id: int | None = None


CommandRecord = CommandRow


@dataclass
class RunMetadataRecord:
    key: str
    value: str


MeasurementRecord = MeasurementRow
VerificationRecord = VerificationRow

_ALLOWED_TABLES = frozenset(
    {
        "measurements",
        "verifications",
        "commands",
        "events",
        "run_metadata",
        "provenance",
    },
)


def is_allowed_table(name: str) -> bool:
    return name in _ALLOWED_TABLES or name.startswith("plugin_")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cursor_rowid(cur: sqlite3.Cursor) -> int:
    rowid = cur.lastrowid
    if rowid is None:
        raise RuntimeError("INSERT did not return a row id")
    return int(rowid)


def _loads_json(value: object) -> object | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes, bytearray)):
        loaded: object = json.loads(value)
        return loaded
    raise TypeError(f"unexpected JSON column value: {type(value)!r}")


def _as_optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError("bool is not a numeric tolerance")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    raise TypeError(f"expected numeric tolerance, got {type(value)!r}")


def _as_int(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"expected integer column value, got {type(value)!r}")


def _measurement_from_lookup(item: tuple[object, ...]) -> MeasurementRow:
    return MeasurementRow(
        domain=str(item[0]),
        command=str(item[1]),
        key=str(item[2]),
        row_index=_as_int(item[3]),
        value=_loads_json(item[4]),
        units=item[5],  # type: ignore[arg-type]
        artifact_path=item[6],  # type: ignore[arg-type]
        status=str(item[7]),
        timestamp=str(item[8]),
        id=_as_int(item[9]) if item[9] is not None else None,
    )


def _measurement_record(item: tuple[object, ...]) -> MeasurementRecord:
    return MeasurementRecord(
        id=_as_int(item[0]),
        domain=str(item[1]),
        command=str(item[2]),
        key=str(item[3]),
        row_index=_as_int(item[4]),
        value=_loads_json(item[5]),
        units=item[6],  # type: ignore[arg-type]
        artifact_path=item[7],  # type: ignore[arg-type]
        status=str(item[8]),
        timestamp=str(item[9]),
    )


def _verification_record(item: tuple[object, ...]) -> VerificationRecord:
    return VerificationRecord(
        id=_as_int(item[0]),
        domain=str(item[1]),
        command=str(item[2]),
        key=str(item[3]),
        expected=_loads_json(item[4]),
        actual=_loads_json(item[5]),
        tolerance=_as_optional_float(_loads_json(item[6])),
        compare_op=item[7],  # type: ignore[arg-type]
        status=str(item[8]),
        optional=bool(item[9]),
        message=item[10],  # type: ignore[arg-type]
        description=item[11],  # type: ignore[arg-type]
        timestamp=str(item[12]),
    )


def _command_record(item: tuple[object, ...]) -> CommandRecord:
    return CommandRecord(
        id=_as_int(item[0]),
        domain=str(item[1]),
        command=str(item[2]),
        key=str(item[3]),
        result=_loads_json(item[4]),
        status=str(item[5]),
        optional=bool(item[6]),
        message=str(item[7] or ""),
        cause=str(item[8] or ""),
        timestamp=str(item[9]),
    )


def _active_ctx() -> RuntimeContext:
    from colosseum.context import get_context

    return get_context()


def read_measurements() -> list[MeasurementRecord]:
    ctx = _active_ctx()
    if not ctx.db.is_initialized():
        raise RuntimeError("Database is not initialized for this run")
    return ctx.db.fetch_all_measurements()


def read_verifications() -> list[VerificationRecord]:
    ctx = _active_ctx()
    if not ctx.db.is_initialized():
        raise RuntimeError("Database is not initialized for this run")
    return ctx.db.fetch_all_verifications()


def read_run_metadata() -> list[RunMetadataRecord]:
    ctx = _active_ctx()
    if not ctx.db.is_initialized():
        raise RuntimeError("Database is not initialized for this run")
    return ctx.db.fetch_run_metadata()


def read_table(name: str) -> list[dict[str, object]]:
    ctx = _active_ctx()
    if not ctx.db.is_initialized():
        raise RuntimeError("Database is not initialized for this run")
    if is_allowed_table(name):
        return ctx.db.fetch_table_rows(name)
    raise ValueError(f"Unknown or disallowed table: {name}")


class DatabaseManager:
    def __init__(self) -> None:
        self._conn: sqlite3.Connection | None = None
        self.defer_commits: bool = False
        self._lock = threading.RLock()
        self._write_queue: DatabaseWriteQueue | None = None
        self._readonly: bool = False
        self._db_path: Path | None = None

    def _maybe_commit(self) -> None:
        if not self.defer_commits:
            self._require_conn().commit()

    def _queue_commit(self) -> None:
        """Commit used by the background writer (always commits the batch)."""
        if self._conn is not None:
            self._conn.commit()

    def flush(self) -> None:
        """Drain the write queue and commit pending writes."""
        self.drain()
        with self._lock:
            if self._conn is not None:
                self._conn.commit()

    def drain(self, *, timeout: float | None = 30.0) -> None:
        """Wait until queued listener writes are durable."""
        if self._write_queue is not None and self._write_queue.started:
            self._write_queue.drain(timeout=timeout)

    def _start_write_queue(self) -> None:
        if self._readonly or self._write_queue is not None:
            return
        self._write_queue = DatabaseWriteQueue(
            lock=self._lock,
            commit=self._queue_commit,
        )
        self._write_queue.start()

    def initialize(self, db_path: Path) -> None:
        if self._conn is not None:
            return
        import os

        self.defer_commits = os.environ.get("COLOSSEUM_DEFER_DB_COMMITS") == "1"
        self._readonly = False
        self._db_path = Path(db_path)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()
        self._start_write_queue()

    def open_readonly(self, db_path: Path) -> None:
        if self._conn is not None:
            raise RuntimeError("Database connection already open")
        resolved = db_path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"Database not found: {resolved}")
        self._db_path = resolved
        uri = f"file:{resolved.as_posix()}?mode=ro"
        self._readonly = True
        self._conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        self._conn.execute("PRAGMA query_only = ON")

    def is_initialized(self) -> bool:
        return self._conn is not None

    def close(self) -> None:
        if self._write_queue is not None:
            try:
                self._write_queue.stop()
            finally:
                self._write_queue = None
        with self._lock:
            if self._conn is not None:
                if self.defer_commits:
                    self._conn.commit()
                self._conn.close()
                self._conn = None
                self._db_path = None
                self.defer_commits = False
                self._readonly = False

    def _require_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database not initialized")
        return self._conn

    def _execute_insert(self, sql: str, params: tuple[object, ...]) -> int:
        with self._lock:
            cur = self._require_conn().execute(sql, params)
            self._maybe_commit()
            return _cursor_rowid(cur)

    def _insert_measurement_unlocked(self, row: MeasurementRow) -> int:
        ts = row.timestamp or _utc_now()
        cur = self._require_conn().execute(
            """
            INSERT INTO measurements
            (domain, command, key, row_index, value_json, units, artifact_path, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.domain,
                row.command,
                row.key,
                row.row_index,
                json.dumps(row.value),
                row.units,
                row.artifact_path,
                row.status,
                ts,
            ),
        )
        return _cursor_rowid(cur)

    def insert_measurement(self, row: MeasurementRow) -> int:
        """Insert a measurement synchronously (script / decorator path)."""
        with self._lock:
            rowid = self._insert_measurement_unlocked(row)
            self._maybe_commit()
            return rowid

    def enqueue_measurement(self, row: MeasurementRow) -> None:
        """Queue a measurement from any thread (e.g. GNSS listener).

        Non-blocking. Durability is ensured by :meth:`drain` / :meth:`flush` /
        :meth:`close`. When the write queue is not running (test helpers),
        inserts synchronously under the lock.
        """
        if self._readonly:
            raise RuntimeError("Database is read-only")
        if self._write_queue is None or not self._write_queue.started:
            self.insert_measurement(row)
            return

        def apply() -> None:
            self._insert_measurement_unlocked(row)

        self._write_queue.put(WriteJob(apply=apply))

    def insert_command(self, row: CommandRow) -> int:
        ts = row.timestamp or _utc_now()
        return self._execute_insert(
            """
            INSERT INTO commands
            (domain, command, key, result_json, status, optional, message, cause, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.domain,
                row.command,
                row.key,
                json.dumps(row.result),
                row.status,
                1 if row.optional else 0,
                row.message,
                row.cause,
                ts,
            ),
        )

    def insert_verification(self, row: VerificationRow) -> int:
        ts = row.timestamp or _utc_now()
        return self._execute_insert(
            """
            INSERT INTO verifications
            (domain, command, key, expected_json, actual_json, tolerance_json, compare_op,
             status, optional, message, description, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.domain,
                row.command,
                row.key,
                json.dumps(row.expected),
                json.dumps(row.actual),
                json.dumps(row.tolerance),
                row.compare_op,
                row.status,
                1 if row.optional else 0,
                row.message,
                row.description,
                ts,
            ),
        )

    def insert_event(self, level: str, source: str, message: str) -> int:
        return self._execute_insert(
            "INSERT INTO events(level, source, message, timestamp) VALUES (?, ?, ?, ?)",
            (level, source, message, _utc_now()),
        )

    def insert_run_metadata(self, key: str, value: str) -> None:
        self._execute_insert(
            "INSERT OR REPLACE INTO run_metadata(key, value) VALUES (?, ?)",
            (key, value),
        )

    def insert_provenance(self, section: str, payload: object) -> None:
        """Store one provenance section. A later write of the same section replaces it."""
        self._execute_insert(
            "INSERT OR REPLACE INTO provenance(section, payload_json) VALUES (?, ?)",
            (section, json.dumps(payload, sort_keys=True)),
        )

    def get_measurement(
        self, domain: str, command: str, key: str, row_index: int = 0,
    ) -> MeasurementRow | None:
        with self._lock:
            conn = self._require_conn()
            cur = conn.execute(
                """
                SELECT domain, command, key, row_index, value_json, units,
                       artifact_path, status, timestamp, id
                FROM measurements WHERE domain=? AND command=? AND key=? AND row_index=?
                ORDER BY id DESC LIMIT 1
                """,
                (domain, command, key, row_index),
            )
            item = cur.fetchone()
            if item is None:
                return None
            return _measurement_from_lookup(item)

    def list_measurements(self, domain: str, command: str, key: str) -> list[MeasurementRow]:
        with self._lock:
            conn = self._require_conn()
            cur = conn.execute(
                """
                SELECT domain, command, key, row_index, value_json, units,
                       artifact_path, status, timestamp, id
                FROM measurements WHERE domain=? AND command=? AND key=? ORDER BY id ASC
                """,
                (domain, command, key),
            )
            return [_measurement_from_lookup(item) for item in cur.fetchall()]

    def fetch_all_measurements(self) -> list[MeasurementRecord]:
        with self._lock:
            conn = self._require_conn()
            cur = conn.execute(
                """
                SELECT id, domain, command, key, row_index, value_json, units,
                       artifact_path, status, timestamp
                FROM measurements ORDER BY id ASC
                """,
            )
            return [_measurement_record(item) for item in cur.fetchall()]

    def fetch_all_verifications(self) -> list[VerificationRecord]:
        with self._lock:
            conn = self._require_conn()
            cur = conn.execute(
                """
                SELECT id, domain, command, key, expected_json, actual_json, tolerance_json,
                       compare_op, status, optional, message, description, timestamp
                FROM verifications ORDER BY id ASC
                """,
            )
            return [_verification_record(item) for item in cur.fetchall()]

    def fetch_all_commands(self) -> list[CommandRecord]:
        with self._lock:
            conn = self._require_conn()
            cur = conn.execute(
                """
                SELECT id, domain, command, key, result_json, status, optional, message,
                       cause, timestamp
                FROM commands ORDER BY id ASC
                """,
            )
            return [_command_record(item) for item in cur.fetchall()]

    def resolve_artifact_path(self, stored: str | None) -> Path | None:
        """Resolve a stored artifact path against this database's run directory.

        Relative paths are joined to the directory that contains
        ``execution.sqlite``. When the row was imported, ``imported_from`` is
        the next place to look. Legacy absolute paths that no longer exist
        (because the run folder was renamed ``-pass`` / ``-fail``) are rebased
        onto that directory when a matching suffix is present.
        """
        if not stored:
            return None
        from colosseum.database.artifact_paths import resolve_stored_artifact

        run_dir = self._db_path.parent if self._db_path is not None else Path.cwd()
        origin: Path | None = None
        if self.is_initialized():
            for item in self.fetch_run_metadata():
                if item.key == "imported_from" and item.value:
                    origin = Path(str(item.value))
                    break
        return resolve_stored_artifact(stored, run_dir=run_dir, import_origin=origin)

    def measurement_keys(self) -> set[str]:
        with self._lock:
            conn = self._require_conn()
            cur = conn.execute("SELECT DISTINCT key FROM measurements")
            return {str(row[0]) for row in cur.fetchall()}

    def fetch_run_metadata(self) -> list[RunMetadataRecord]:
        with self._lock:
            conn = self._require_conn()
            cur = conn.execute("SELECT key, value FROM run_metadata ORDER BY key ASC")
            return [RunMetadataRecord(key=item[0], value=item[1]) for item in cur.fetchall()]

    def fetch_table_rows(self, name: str) -> list[dict[str, object]]:
        query = _TABLE_SELECT_SQL.get(name)
        if query is None:
            raise ValueError(f"Invalid table name: {name}")
        with self._lock:
            conn = self._require_conn()
            cur = conn.execute(query)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def count_rows(
        self, table: str, where: str = "", params: tuple[object, ...] = (),
    ) -> int:
        if where:
            if "".join(where.split()) != "key=?":
                raise ValueError("count_rows where must be 'key=?' with one bound parameter")
            if len(params) != 1:
                raise ValueError("count_rows where key=? requires exactly one parameter")
            query = _TABLE_COUNT_KEY_SQL.get(table)
        else:
            if params:
                raise ValueError("count_rows parameters require a where clause")
            query = _TABLE_COUNT_SQL.get(table)
        if query is None:
            raise ValueError(f"Invalid table name: {table}")
        with self._lock:
            conn = self._require_conn()
            cur = conn.execute(query, params)
            row = cur.fetchone()
            if row is None:
                return 0
            return int(row[0])


def initialize_database_if_needed(ctx: RuntimeContext) -> None:
    if not ctx.db.is_initialized():
        if ctx.no_artifacts:
            db_path = Path(":memory:")
        elif ctx.output_dir is None:
            raise RuntimeError("Output directory must be allocated before DB init")
        else:
            db_path = ctx.output_dir / "execution.sqlite"
        ctx.db.initialize(db_path)
        if ctx.logger is not None:
            ctx.logger.debug("Initialized execution database: %s", db_path)
        ctx.db.insert_run_metadata("test_case_name", ctx.test_case_name)
        ctx.db.insert_run_metadata("suite_name", ctx.suite_name or "")
        ctx.db.insert_run_metadata("config_path", str(ctx.config_path) if ctx.config_path else "")
