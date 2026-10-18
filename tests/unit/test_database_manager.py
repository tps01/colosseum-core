"""U-DB-01: SQLite manager round-trip."""

from __future__ import annotations

import pytest

from colosseum.database.manager import DatabaseManager, MeasurementRow


def test_shared_unit_db_truncates_between_connections(unit_test_db, unit_test_db_uri: str) -> None:
    from tests.unit.db_unit import connect_unit_test_db, truncate_unit_test_db

    first = DatabaseManager()
    connect_unit_test_db(first, unit_test_db_uri)
    first.insert_measurement(
        MeasurementRow(domain="equipment", command="measure_voltage", key="iso", value=1.0)
    )
    assert first.count_rows("measurements") == 1
    first.close()

    truncate_unit_test_db(unit_test_db)

    second = DatabaseManager()
    connect_unit_test_db(second, unit_test_db_uri)
    try:
        assert second.count_rows("measurements") == 0
    finally:
        second.close()


def test_measurement_json_round_trip(db: DatabaseManager) -> None:
    db.insert_measurement(
        MeasurementRow(domain="equipment", command="measure_voltage", key="v", value={"v": 3.3})
    )
    row = db.get_measurement("equipment", "measure_voltage", "v")
    assert row is not None
    assert row.value == {"v": 3.3}
    assert row.status == "PASS"


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
