"""Unit tests for offline database reads."""

from __future__ import annotations

import colosseum as col
from colosseum.config import load_config
from colosseum.database.read_from_path import read_from_path

from tests.support.helpers import latest_output_dir, run_endex_expect_code


def test_read_from_path_measurements_and_verifications(bench_sim, isolated_cwd) -> None:
    load_config(bench_sim)
    col.equipment.dmm.measure_voltage(dmm_id=1, channel=1, key="offline_key")
    col.equipment.dmm.verify_voltage(key="offline_key", expected_val=3.3, tolerance=0.5)
    run_endex_expect_code(0)
    run_dir = latest_output_dir(isolated_cwd)
    db_path = run_dir / "execution.sqlite"

    with read_from_path(db_path) as reader:
        measurements = reader.read_measurements()
        verifications = reader.read_verifications()
        metadata = reader.read_run_metadata()
        events = reader.read_table("events")

    keys = {m.key for m in measurements}
    assert "offline_key" in keys
    assert any(v.key == "offline_key" for v in verifications)
    assert any(m.key == "test_case_name" for m in metadata)
    assert isinstance(events, list)


def test_read_from_path_missing_file(isolated_cwd) -> None:
    db_path = isolated_cwd / "missing.sqlite"
    try:
        read_from_path(db_path)
        raised = False
    except FileNotFoundError:
        raised = True
    assert raised


def test_read_from_path_rejects_disallowed_table(bench_sim, isolated_cwd) -> None:
    load_config(bench_sim)
    run_endex_expect_code(0)
    run_dir = latest_output_dir(isolated_cwd)

    with read_from_path(run_dir / "execution.sqlite") as reader:
        try:
            reader.read_table("sqlite_master")
            raised = False
        except ValueError:
            raised = True

    assert raised
