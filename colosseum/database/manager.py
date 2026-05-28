from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Optional

from .schema import SCHEMA_SQL


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MeasurementRow:
    domain: str
    command: str
    key: str
    row_index: int = 0
    value: object = None
    units: Optional[str] = None
    artifact_path: Optional[str] = None
    status: str = "PASS"
    timestamp: str = ""


@dataclass
class VerificationRow:
    domain: str
    command: str
    key: str
    expected: object = None
    actual: object = None
    status: str = "PASS"
    optional: bool = False
    message: str = ""
    timestamp: str = ""


class DatabaseManager:
    def __init__(self) -> None:
        self._conn: Optional[sqlite3.Connection] = None

    def initialize(self, db_path: Path) -> None:
        if self._conn is not None:
            return
        self._conn = sqlite3.connect(str(db_path))
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    def is_initialized(self) -> bool:
        return self._conn is not None

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _require_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database not initialized")
        return self._conn

    def insert_measurement(self, row: MeasurementRow) -> int:
        conn = self._require_conn()
        ts = row.timestamp or _utc_now()
        cur = conn.execute(
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
        conn.commit()
        return int(cur.lastrowid)

    def insert_verification(self, row: VerificationRow) -> int:
        conn = self._require_conn()
        ts = row.timestamp or _utc_now()
        cur = conn.execute(
            """
            INSERT INTO verifications
            (domain, command, key, expected_json, actual_json, status, optional, message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.domain,
                row.command,
                row.key,
                json.dumps(row.expected),
                json.dumps(row.actual),
                row.status,
                1 if row.optional else 0,
                row.message,
                ts,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)

    def insert_event(self, level: str, source: str, message: str) -> int:
        conn = self._require_conn()
        cur = conn.execute(
            "INSERT INTO events(level, source, message, timestamp) VALUES (?, ?, ?, ?)",
            (level, source, message, _utc_now()),
        )
        conn.commit()
        return int(cur.lastrowid)

    def insert_run_metadata(self, key: str, value: str) -> None:
        conn = self._require_conn()
        conn.execute("INSERT OR REPLACE INTO run_metadata(key, value) VALUES (?, ?)", (key, value))
        conn.commit()

    def insert_artifact(self, kind: str, path: str, description: str = "") -> int:
        conn = self._require_conn()
        cur = conn.execute(
            "INSERT INTO artifacts(kind, path, description, timestamp) VALUES (?, ?, ?, ?)",
            (kind, path, description, _utc_now()),
        )
        conn.commit()
        return int(cur.lastrowid)

    def get_measurement(self, domain: str, command: str, key: str, row_index: int = 0) -> Optional[MeasurementRow]:
        conn = self._require_conn()
        cur = conn.execute(
            """
            SELECT domain, command, key, row_index, value_json, units, artifact_path, status, timestamp
            FROM measurements WHERE domain=? AND command=? AND key=? AND row_index=?
            ORDER BY id DESC LIMIT 1
            """,
            (domain, command, key, row_index),
        )
        item = cur.fetchone()
        if item is None:
            return None
        return MeasurementRow(
            domain=item[0],
            command=item[1],
            key=item[2],
            row_index=item[3],
            value=json.loads(item[4]) if item[4] is not None else None,
            units=item[5],
            artifact_path=item[6],
            status=item[7],
            timestamp=item[8],
        )

    def list_measurements(self, domain: str, command: str, key: str) -> list[MeasurementRow]:
        conn = self._require_conn()
        cur = conn.execute(
            """
            SELECT domain, command, key, row_index, value_json, units, artifact_path, status, timestamp
            FROM measurements WHERE domain=? AND command=? AND key=? ORDER BY id ASC
            """,
            (domain, command, key),
        )
        out: list[MeasurementRow] = []
        for item in cur.fetchall():
            out.append(
                MeasurementRow(
                    domain=item[0],
                    command=item[1],
                    key=item[2],
                    row_index=item[3],
                    value=json.loads(item[4]) if item[4] is not None else None,
                    units=item[5],
                    artifact_path=item[6],
                    status=item[7],
                    timestamp=item[8],
                )
            )
        return out

    def fetch_all_measurements(self) -> list:
        from .records import MeasurementRecord

        conn = self._require_conn()
        cur = conn.execute(
            """
            SELECT id, domain, command, key, row_index, value_json, units, artifact_path, status, timestamp
            FROM measurements ORDER BY id ASC
            """
        )
        rows = []
        for item in cur.fetchall():
            rows.append(
                MeasurementRecord(
                    id=item[0],
                    domain=item[1],
                    command=item[2],
                    key=item[3],
                    row_index=item[4],
                    value=json.loads(item[5]) if item[5] is not None else None,
                    units=item[6],
                    artifact_path=item[7],
                    status=item[8],
                    timestamp=item[9],
                )
            )
        return rows

    def fetch_all_verifications(self) -> list:
        from .records import VerificationRecord

        conn = self._require_conn()
        cur = conn.execute(
            """
            SELECT id, domain, command, key, expected_json, actual_json, status, optional, message, timestamp
            FROM verifications ORDER BY id ASC
            """
        )
        rows = []
        for item in cur.fetchall():
            rows.append(
                VerificationRecord(
                    id=item[0],
                    domain=item[1],
                    command=item[2],
                    key=item[3],
                    expected=json.loads(item[4]) if item[4] is not None else None,
                    actual=json.loads(item[5]) if item[5] is not None else None,
                    status=item[6],
                    optional=bool(item[7]),
                    message=item[8],
                    timestamp=item[9],
                )
            )
        return rows

    def fetch_run_metadata(self) -> list:
        from .records import RunMetadataRecord

        conn = self._require_conn()
        cur = conn.execute("SELECT key, value FROM run_metadata ORDER BY key ASC")
        return [RunMetadataRecord(key=item[0], value=item[1]) for item in cur.fetchall()]

    def fetch_table_rows(self, name: str) -> list[dict]:
        import re

        if not re.match(r"^[A-Za-z0-9_]+$", name):
            raise ValueError(f"Invalid table name: {name}")
        conn = self._require_conn()
        cur = conn.execute(f"SELECT * FROM {name}")
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def count_rows(self, table: str, where: str = "", params: tuple = ()) -> int:
        conn = self._require_conn()
        query = f"SELECT COUNT(*) FROM {table}"
        if where:
            query += f" WHERE {where}"
        cur = conn.execute(query, params)
        return int(cur.fetchone()[0])


def initialize_database_if_needed(ctx) -> None:
    if ctx.output_dir is None:
        raise RuntimeError("Output directory must be allocated before DB init")
    if not ctx.db.is_initialized():
        ctx.db.initialize(ctx.output_dir / "execution.sqlite")
        ctx.db.insert_run_metadata("test_case_name", ctx.test_case_name)
        ctx.db.insert_run_metadata("suite_name", ctx.suite_name or "")
        ctx.db.insert_run_metadata("config_path", str(ctx.config_path) if ctx.config_path else "")
