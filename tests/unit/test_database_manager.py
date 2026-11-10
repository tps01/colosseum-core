"""U-DB-01: SQLite manager round-trip."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from colosseum.database.manager import DatabaseManager, MeasurementRow


def test_disk_commit_visibility_follows_defer_setting(tmp_path, monkeypatch) -> None:
    """Default commits are visible to another connection; deferred commits wait for close."""
    import sqlite3

    row = MeasurementRow(domain="equipment", command="measure_voltage", key="iso", value=1.0)

    monkeypatch.delenv("COLOSSEUM_DEFER_DB_COMMITS", raising=False)
    immediate = tmp_path / "immediate.sqlite"
    manager = DatabaseManager()
    manager.initialize(immediate)
    try:
        manager.insert_measurement(row)
        with sqlite3.connect(immediate) as other:
            assert other.execute("SELECT COUNT(*) FROM measurements").fetchone()[0] == 1
    finally:
        manager.close()

    monkeypatch.setenv("COLOSSEUM_DEFER_DB_COMMITS", "1")
    deferred = tmp_path / "deferred.sqlite"
    manager = DatabaseManager()
    manager.initialize(deferred)
    try:
        manager.insert_measurement(row)
        with sqlite3.connect(deferred) as other:
            assert other.execute("SELECT COUNT(*) FROM measurements").fetchone()[0] == 0
    finally:
        manager.close()
    with sqlite3.connect(deferred) as other:
        assert other.execute("SELECT COUNT(*) FROM measurements").fetchone()[0] == 1


def test_measurements_schema_and_autocincrement(tmp_path, monkeypatch) -> None:
    """Protected measurement columns, lookup index, and AUTOINCREMENT identity."""
    import sqlite3

    monkeypatch.delenv("COLOSSEUM_DEFER_DB_COMMITS", raising=False)
    path = tmp_path / "execution.sqlite"
    manager = DatabaseManager()
    manager.initialize(path)
    try:
        manager.insert_measurement(
            MeasurementRow(domain="core", command="measure", key="first", value=1),
        )
        with sqlite3.connect(path) as connection:
            connection.execute("DELETE FROM measurements")
            connection.commit()
        manager.insert_measurement(
            MeasurementRow(domain="core", command="measure", key="second", value=2),
        )
        second = manager.get_measurement("core", "measure", "second")
        assert second is not None and second.id == 2
    finally:
        manager.close()

    with sqlite3.connect(path) as connection:
        columns = connection.execute("PRAGMA table_info(measurements)").fetchall()
        defined = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='measurements'",
        ).fetchone()
        index = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_measurements_lookup'",
        ).fetchone()
    assert defined is not None and "AUTOINCREMENT" in defined[0]
    assert index is not None
    assert "domain" in index[0] and "command" in index[0] and "key" in index[0]
    observed = [(row[1], row[2], row[3], row[4], row[5]) for row in columns]
    assert observed == [
        ("id", "INTEGER", 0, None, 1),
        ("domain", "TEXT", 1, None, 0),
        ("command", "TEXT", 1, None, 0),
        ("key", "TEXT", 1, None, 0),
        ("row_index", "INTEGER", 1, "0", 0),
        ("value_json", "TEXT", 0, None, 0),
        ("units", "TEXT", 0, None, 0),
        ("artifact_path", "TEXT", 0, None, 0),
        ("status", "TEXT", 1, None, 0),
        ("timestamp", "TEXT", 1, None, 0),
    ]


def test_measurement_json_round_trip(db: DatabaseManager) -> None:
    db.insert_measurement(MeasurementRow(domain="equipment", command="measure_voltage", key="v", value={"v": 3.3}))
    row = db.get_measurement("equipment", "measure_voltage", "v")
    assert row is not None
    assert row.value == {"v": 3.3}
    assert row.status == "PASS"


def test_requirement_attachments_keep_source_order_and_rollback(db):
    import sqlite3
    from colosseum.database import VerificationRow

    row = VerificationRow(
        domain="core",
        command="check",
        key="v",
        expected=1,
        actual=1,
        tolerance=None,
        compare_op="EQ",
        status="PASS",
        optional=False,
        requirements=["R-2", "R-1", "R-2"],
    )
    rowid = db.insert_verification(row)
    stored = db.fetch_all_verifications()
    assert [(item.id, item.requirements) for item in stored] == [(rowid, row.requirements)]
    row.requirements = ["valid", object()]
    # CPython 3.9 reports an unbound parameter as InterfaceError. 3.12 reports
    # ProgrammingError. Either way the savepoint rolls the partial insert back.
    with pytest.raises((sqlite3.ProgrammingError, sqlite3.InterfaceError)):
        db.insert_verification(row)
    assert db.count_rows("verifications") == 1
    assert len(db.fetch_table_rows("verification_requirements")) == 3


def test_result_and_metadata_commit_atomically(db):
    import sqlite3

    conn = db._require_conn()
    conn.execute(
        "CREATE TRIGGER reject_result BEFORE INSERT ON run_metadata "
        "BEGIN SELECT RAISE(ABORT, 'storage failure'); END"
    )
    try:
        with pytest.raises(sqlite3.IntegrityError, match="storage failure"):
            db.store_result({"overall_result": "PASS", "exit_code": 0, "end_time_utc": "now"}, kind="single")
        assert db.fetch_table_rows("run_result") == []
        assert db.fetch_run_metadata() == []
    finally:
        conn.execute("DROP TRIGGER reject_result")


def test_old_readonly_evidence_without_requirement_table(tmp_path):
    from colosseum.database import VerificationRow

    path = tmp_path / "legacy.sqlite"
    db = DatabaseManager()
    db.initialize(path)
    db.insert_verification(
        VerificationRow(
            domain="core",
            command="check",
            key="v",
            expected=1,
            actual=1,
            tolerance=None,
            compare_op="EQ",
            status="PASS",
            optional=False,
        )
    )
    db._require_conn().execute("DROP TABLE verification_requirements")
    db.flush()
    db.close()
    db.open_readonly(path)
    try:
        assert db.fetch_all_verifications()[0].requirements == []
        assert "verification_requirements" not in {
            row[0] for row in db._require_conn().execute("SELECT name FROM sqlite_master")
        }
    finally:
        db.close()


def test_measurement_json_dumps_datetime(db: DatabaseManager) -> None:
    when = datetime(2026, 10, 25, 21, 50, tzinfo=timezone.utc)
    db.insert_measurement(
        MeasurementRow(
            domain="equipment",
            command="measure_voltage",
            key="when",
            value={"captured_at": when},
        ),
    )
    row = db.get_measurement("equipment", "measure_voltage", "when")
    assert row is not None
    assert row.value == {"captured_at": str(when)}


def test_fetch_table_rejects_invalid_name(db: DatabaseManager) -> None:
    with pytest.raises(ValueError, match="Invalid table name"):
        db.fetch_table_rows("measurements; DROP TABLE measurements")


def test_enqueue_measurement_from_background_thread(tmp_path) -> None:
    import threading

    db = DatabaseManager()
    db.initialize(tmp_path / "execution.sqlite")
    try:
        errors: list[BaseException] = []

        def worker() -> None:
            try:
                for index in range(20):
                    db.enqueue_measurement(
                        MeasurementRow(
                            domain="equipment",
                            command="track_epoch",
                            key="soak",
                            row_index=index,
                            value={"i": index},
                        ),
                    )
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=5)
        assert not errors
        db.drain()
        assert db.count_rows("measurements") == 20
        rows = db.list_measurements("equipment", "track_epoch", "soak")
        assert [row.row_index for row in rows] == list(range(20))
    finally:
        db.close()
