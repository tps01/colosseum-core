"""Operator results table, limits, and evidence links."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from colosseum.database.schema import SCHEMA_SQL
from colosseum.gui._evidence import links_for_row, unassociated_files
from colosseum.gui._plots import explicit_xy, limit_fraction, limit_view, reduce_xy
from colosseum.gui._results import EvidenceRow, filter_rows, load_run_evidence


def _row(**overrides: object) -> EvidenceRow:
    base = EvidenceRow(
        kind="verification",
        record_id=1,
        status="FAIL",
        optional=False,
        step="rail_v",
        key="rail_v",
        actual="2.9",
        comparison="3.3 ± 0",
        units="",
        message="low",
        domain="core",
        command="verify_rail_v",
        expected_raw="3.3",
        actual_raw="2.9",
        tolerance_raw="0",
        compare_op="GELE",
        artifact_stored="",
        cause="",
    )
    data = base.__dict__.copy()
    data.update(overrides)
    return EvidenceRow(**data)


def test_failures_filter_keeps_required_errors_and_hides_optional() -> None:
    rows = [
        _row(),
        _row(record_id=2, status="ERROR", kind="command", optional=False, step="arm"),
        _row(record_id=3, status="FAIL", optional=True, step="note"),
        _row(record_id=4, status="PASS", step="link"),
        _row(record_id=5, kind="measurement", status="PASS", step="rail_v"),
    ]
    failed = filter_rows(rows, failures_only=True)
    assert [row.record_id for row in failed] == [1, 2]
    assert [row.record_id for row in filter_rows(rows, text="link")] == [4]


def test_load_run_evidence_reads_sqlite_without_writing(tmp_path: Path) -> None:
    database = tmp_path / "execution.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript(SCHEMA_SQL)
    connection.execute(
        "INSERT INTO verifications (domain, command, key, expected_json, actual_json, "
        "tolerance_json, compare_op, status, optional, message, step_name, timestamp) "
        "VALUES ('core', 'verify_rail_v', 'rail_v', '3.3', '2.9', '0.0', 'GELE', 'FAIL', 0, "
        "'below', 'rail', 't')",
    )
    connection.execute(
        "INSERT INTO commands (domain, command, key, result_json, status, optional, message, "
        "cause, timestamp) VALUES ('core', 'arm', 'dev', 'null', 'ERROR', 0, 'boom', "
        "'procedural', 't')",
    )
    connection.commit()
    connection.close()
    before = database.read_bytes()
    loaded = load_run_evidence(tmp_path)
    assert database.read_bytes() == before
    assert loaded.error is None
    assert any(row.kind == "verification" and row.comparison == "3.3 ± 0" for row in loaded.rows)
    assert any(row.kind == "command" and row.status == "ERROR" for row in loaded.rows)


def test_load_run_evidence_reads_sqlite_without_later_columns(tmp_path: Path) -> None:
    database = tmp_path / "execution.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE verifications (
          id INTEGER PRIMARY KEY,
          domain TEXT, command TEXT, key TEXT,
          expected_json TEXT, actual_json TEXT,
          status TEXT, optional INTEGER, message TEXT, timestamp TEXT
        );
        CREATE TABLE commands (
          id INTEGER PRIMARY KEY,
          domain TEXT, command TEXT, key TEXT,
          result_json TEXT, status TEXT, optional INTEGER, message TEXT, timestamp TEXT
        );
        CREATE TABLE measurements (
          id INTEGER PRIMARY KEY,
          domain TEXT, command TEXT, key TEXT,
          row_index INTEGER, value_json TEXT, units TEXT, artifact_path TEXT,
          status TEXT, timestamp TEXT
        );
        """,
    )
    connection.execute(
        "INSERT INTO verifications (domain, command, key, expected_json, actual_json, "
        "status, optional, message, timestamp) VALUES ('core', 'verify_send', 'hello', "
        "'1', 'null', 'ERROR', 0, 'no measurement', 't')",
    )
    connection.execute(
        "INSERT INTO commands (domain, command, key, result_json, status, optional, "
        "message, timestamp) VALUES ('core', 'send', 'hello', 'null', 'PASS', 0, '', 't')",
    )
    connection.commit()
    connection.close()
    loaded = load_run_evidence(tmp_path)
    assert loaded.error is None
    verification = next(row for row in loaded.rows if row.kind == "verification")
    command = next(row for row in loaded.rows if row.kind == "command")
    assert verification.status == "ERROR"
    assert verification.compare_op == ""
    assert command.cause == ""
    assert command.status == "PASS"


def test_limit_view_rejects_non_numeric_and_keeps_one_sided_bounds() -> None:
    assert limit_view(
        compare_op="GE", expected_raw="3.3", tolerance_raw="", actual_raw="2.9", units="V",
    ) == limit_view(
        compare_op="GE", expected_raw="3.3", tolerance_raw="", actual_raw="2.9", units="V",
    )
    view = limit_view(
        compare_op="GE", expected_raw="3.3", tolerance_raw="", actual_raw="2.9", units="V",
    )
    assert view is not None
    assert view.low == 3.3
    assert view.high is None
    assert limit_view(
        compare_op="EQ", expected_raw='"up"', tolerance_raw="", actual_raw='"down"', units="",
    ) is None


def test_limit_window_uses_one_zoom_for_the_same_limits() -> None:
    assert abs(limit_fraction(8, 8, 12) - 0.2) < 1e-9
    assert abs(limit_fraction(12, 8, 12) - 0.8) < 1e-9
    assert limit_fraction(100, 8, 12) == 1.0
    assert limit_fraction(-50, 8, 12) == 0.0
    assert abs(limit_fraction(10, 10, 10) - 0.5) < 1e-9
    assert limit_fraction(1000, 10, 10) == 1.0
    assert abs(limit_fraction(11, 10, 10) - 0.75) < 1e-9
    assert abs(limit_fraction(8, 8, None) - 0.25) < 1e-9
    assert abs(limit_fraction(12, None, 12) - 0.75) < 1e-9
    assert limit_fraction(0, 0, 0) == 0.5


def test_explicit_xy_requires_declared_axes_and_keeps_spikes() -> None:
    assert explicit_xy("[1, 2, 3]") is None
    series = explicit_xy(
        {"x": [0, 1, 2], "y": [0, 1, float("nan")], "x_unit": "s", "y_unit": "V"},
    )
    assert series is not None
    assert series.points[2] == (2.0, None)
    points = [(float(index), 0.0) for index in range(30)]
    points[17] = (17.0, 9.0)
    reduced = reduce_xy(points, low=0.0, high=1.0, max_points=8)
    assert (17.0, 9.0) in reduced
    assert len(reduced) < len(points)


def test_artifact_link_uses_only_a_unique_measurement(tmp_path: Path) -> None:
    capture = tmp_path / "shot.png"
    capture.write_bytes(b"\x89PNG\r\n")
    measurement = _row(
        kind="measurement", record_id=9, artifact_stored="shot.png", key="rail_v",
        domain="core", command="verify_rail_v",
    )
    verification = _row(artifact_stored="")
    linked = links_for_row(
        verification, [verification, measurement], run_dir=tmp_path, import_origin=None,
    )
    assert len(linked) == 1
    assert linked[0].exists
    second = _row(
        kind="measurement", record_id=10, artifact_stored="other.png", key="rail_v",
        domain="core", command="verify_rail_v",
    )
    assert links_for_row(
        verification, [verification, measurement, second], run_dir=tmp_path, import_origin=None,
    ) == []
    loose = tmp_path / "note.txt"
    loose.write_text("hello", encoding="utf-8")
    extras = unassociated_files(tmp_path, linked)
    assert any(item.path.name == "note.txt" and not item.associated for item in extras)


def test_renamed_run_resolves_relative_artifact(tmp_path: Path) -> None:
    renamed = tmp_path / "run-fail"
    renamed.mkdir()
    (renamed / "shot.png").write_bytes(b"png")
    row = _row(kind="measurement", artifact_stored="shot.png")
    linked = links_for_row(row, [row], run_dir=renamed, import_origin=None)
    assert linked[0].path == (renamed / "shot.png").resolve()
