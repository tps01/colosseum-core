"""I-RUN: endex, artifacts, read API."""

from __future__ import annotations

import pytest

import colosseum as col
from colosseum.config import load_config

from tests.conftest import latest_output_dir, query_db, run_endex_expect_code


def test_decorators_create_sqlite_log_and_summary(bench_sim, isolated_cwd) -> None:
    load_config(bench_sim)
    col.equipment.psu.set_voltage(psu_id=1, voltage=3.3)
    col.equipment.psu.set_output(psu_id=1, enabled=True)
    col.equipment.dmm.measure_voltage(dmm_id=1, channel=1, key="v1")
    run_endex_expect_code(0)
    run_dir = latest_output_dir(isolated_cwd)
    assert (run_dir / "debug.log").is_file()
    assert (run_dir / "execution.sqlite").is_file()
    tables = {
        row[0]
        for row in query_db(run_dir, "SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"run_metadata", "measurements", "verifications", "events", "artifacts"} <= tables
    summary = (run_dir / "summary.txt").read_text(encoding="utf-8")
    assert "Overall result: PASS" in summary
    import json

    payload = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert payload["overall_result"] == "PASS"
    assert payload["exit_code"] == 0


def test_read_api_returns_measurement_keys(bench_sim, isolated_cwd) -> None:
    load_config(bench_sim)
    col.equipment.dmm.measure_voltage(dmm_id=1, channel=1, key="read_key")
    keys = {m.key for m in col.database.read_measurements()}
    assert "read_key" in keys
    run_endex_expect_code(0)


def test_missing_measurement_yields_exit_one(bench_sim, isolated_cwd) -> None:
    load_config(bench_sim)
    col.equipment.dmm.verify_voltage(key="missing_rail", expected_val=1.0, tolerance=0.1)
    run_endex_expect_code(1)
    run_dir = latest_output_dir(isolated_cwd)
    status = query_db(
        run_dir,
        "SELECT status FROM verifications WHERE key=?",
        ("missing_rail",),
    )
    assert status and status[0][0] == "ERROR"


def test_endex_second_call_reuses_final_exit_code(bench_sim, isolated_cwd) -> None:
    load_config(bench_sim)
    col.equipment.dmm.verify_voltage(key="missing_rail", expected_val=1.0, tolerance=0.1)
    run_endex_expect_code(1)
    with pytest.raises(SystemExit) as exc:
        col.endex()
    assert exc.value.code == 1


def test_optional_fail_still_exits_zero(bench_sim, isolated_cwd) -> None:
    load_config(bench_sim)
    col.equipment.psu.set_voltage(psu_id=1, voltage=3.3)
    col.equipment.psu.set_output(psu_id=1, enabled=True)
    col.equipment.dmm.measure_voltage(dmm_id=1, channel=1, key="vrail_3v3")
    col.equipment.dmm.verify_voltage(key="vrail_3v3", expected_val=3.3, tolerance=0.1)
    col.equipment.dmm.measure_voltage(dmm_id=1, channel=2, key="probe_optional")
    col.equipment.dmm.verify_voltage(
        key="probe_optional", expected_val=1.8, tolerance=0.1, optional=True
    )
    run_endex_expect_code(0)
    run_dir = latest_output_dir(isolated_cwd)
    row = col.context.require_context()
    # context finalized; query sqlite directly
    import sqlite3

    conn = sqlite3.connect(run_dir / "execution.sqlite")
    opt = conn.execute(
        "SELECT status FROM verifications WHERE key=? AND optional=1",
        ("probe_optional",),
    ).fetchone()
    conn.close()
    assert opt is not None and opt[0] == "FAIL"
