"""Unit tests for importing prior-run evidence."""

from __future__ import annotations

import sqlite3

from colosseum.context import init_context
from colosseum.database import CommandRow, MeasurementRow
from colosseum.database.evidence_import import import_evidence_from_previous


def test_import_evidence_from_previous(tmp_path, isolated_cwd) -> None:
    source_dir = tmp_path / "prior-pass"
    source_dir.mkdir()
    source_ctx = init_context(test_case_name="prior", no_artifacts=False)
    source_ctx.output_dir = source_dir
    source_ctx.runtime_ready = True
    source_ctx.db.initialize(source_dir / "execution.sqlite")
    source_ctx.db.insert_measurement(
        MeasurementRow(domain="core", command="measure_value", key="stored", value=4.2),
    )
    source_ctx.db.insert_command(
        CommandRow(domain="stub", command="ping", key="k1", result={"ok": True}),
    )
    source_ctx.db.close()

    target_ctx = init_context(test_case_name="rerun", no_artifacts=False)
    target_ctx.output_dir = isolated_cwd / "outputs" / "2026-01-01_120000_rerun"
    target_ctx.output_dir.mkdir(parents=True)
    target_ctx.db.initialize(target_ctx.output_dir / "execution.sqlite")
    target_ctx.runtime_ready = True

    import_evidence_from_previous(target_ctx, source_dir)

    row = target_ctx.db.get_measurement("core", "measure_value", "stored")
    assert row is not None
    assert row.value == 4.2
    commands = target_ctx.db.fetch_table_rows("commands")
    assert len(commands) == 1
    metadata = {item.key: item.value for item in target_ctx.db.fetch_run_metadata()}
    assert metadata["imported_from"] == str(source_dir)


def test_import_old_sqlite_without_cause_column(tmp_path, isolated_cwd) -> None:
    """Older databases omit ``commands.cause``; import still loads rows."""
    source_dir = tmp_path / "prior-old"
    source_dir.mkdir()
    db_path = source_dir / "execution.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE measurements (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          domain TEXT NOT NULL,
          command TEXT NOT NULL,
          key TEXT NOT NULL,
          row_index INTEGER NOT NULL DEFAULT 0,
          value_json TEXT,
          units TEXT,
          artifact_path TEXT,
          status TEXT NOT NULL,
          timestamp TEXT NOT NULL
        );
        CREATE TABLE commands (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          domain TEXT NOT NULL,
          command TEXT NOT NULL,
          key TEXT NOT NULL DEFAULT '',
          result_json TEXT,
          status TEXT NOT NULL,
          optional INTEGER NOT NULL DEFAULT 0,
          message TEXT,
          timestamp TEXT NOT NULL
        );
        INSERT INTO measurements
          (domain, command, key, row_index, value_json, units, artifact_path, status, timestamp)
          VALUES ('core', 'measure_value', 'stored', 0, '1.5', '', NULL, 'PASS', '2026-01-01T00:00:00Z');
        INSERT INTO commands
          (domain, command, key, result_json, status, optional, message, timestamp)
          VALUES ('stub', 'ping', 'k1', 'true', 'PASS', 0, '', '2026-01-01T00:00:00Z');
        """,
    )
    conn.commit()
    conn.close()

    target_ctx = init_context(test_case_name="rerun_old", no_artifacts=False)
    target_ctx.output_dir = isolated_cwd / "outputs" / "2026-01-01_120000_rerun_old"
    target_ctx.output_dir.mkdir(parents=True)
    target_ctx.db.initialize(target_ctx.output_dir / "execution.sqlite")
    target_ctx.runtime_ready = True

    import_evidence_from_previous(target_ctx, source_dir)

    row = target_ctx.db.get_measurement("core", "measure_value", "stored")
    assert row is not None
    assert row.value == 1.5
    commands = target_ctx.db.fetch_table_rows("commands")
    assert len(commands) == 1
    assert commands[0].get("cause", "") in ("", None)
