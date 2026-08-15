"""Unit tests for offline database reads."""

from __future__ import annotations

from colosseum.config import load_config
from colosseum.database.read_from_path import read_from_path

from tests.support.core_api import measure_value, verify_value
from tests.support.helpers import latest_output_dir, run_endex_expect_code


def test_read_from_path_measurements_and_verifications(core_config, isolated_cwd) -> None:
    load_config(core_config)
    measure_value(key="offline_key", value=3.3)
    verify_value(key="offline_key", expected_val=3.3, tolerance=0.5)
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


def test_read_from_path_rejects_disallowed_table(core_config, isolated_cwd) -> None:
    load_config(core_config)
    run_endex_expect_code(0)
    run_dir = latest_output_dir(isolated_cwd)

    with read_from_path(run_dir / "execution.sqlite") as reader:
        try:
            reader.read_table("sqlite_master")
            raised = False
        except ValueError:
            raised = True

    assert raised
