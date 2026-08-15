"""Unit tests for output run directory helpers."""

from __future__ import annotations

import time

from colosseum.config import load_config
from colosseum.output.paths import sanitize_logical_name
from colosseum.output.runs import find_run_directory, list_run_directories, read_summary_json

from tests.support.core_api import measure_value
from tests.support.helpers import latest_output_dir, run_endex_expect_code


def test_sanitize_logical_name_strips_invalid_chars() -> None:
    assert sanitize_logical_name("test power!") == "test_power"
    assert sanitize_logical_name("") == "run"


def test_list_run_directories_empty_when_no_outputs(isolated_cwd) -> None:
    assert list_run_directories(isolated_cwd) == []


def test_list_and_find_after_run(core_config, isolated_cwd) -> None:
    load_config(core_config)
    measure_value(key="k1", value=3.3)
    run_endex_expect_code(0)
    run_dir = latest_output_dir(isolated_cwd)
    runs = list_run_directories(isolated_cwd)
    assert runs[0] == run_dir

    summary = read_summary_json(run_dir)
    assert summary is not None
    logical_name = summary["test_case"]
    assert find_run_directory(isolated_cwd, logical_name) == run_dir


def test_find_run_directory_respects_since(isolated_cwd) -> None:
    outputs = isolated_cwd / "outputs"
    outputs.mkdir()
    old = outputs / "2020-01-01_000000_old_run"
    old.mkdir()
    old.touch()
    time.sleep(0.05)
    since = time.time()
    time.sleep(0.05)
    new = outputs / "2026-01-01_120000_smoke"
    new.mkdir()
    assert find_run_directory(isolated_cwd, "smoke", since=since) == new
    assert find_run_directory(isolated_cwd, "old_run", since=since) is None


def test_find_run_directory_collision_suffix(isolated_cwd) -> None:
    outputs = isolated_cwd / "outputs"
    outputs.mkdir()
    run_dir = outputs / "2026-01-01_120000_smoke_1"
    run_dir.mkdir()
    assert find_run_directory(isolated_cwd, "smoke") == run_dir


def test_read_summary_json_missing(isolated_cwd) -> None:
    run_dir = isolated_cwd / "outputs" / "empty_run"
    run_dir.mkdir(parents=True)
    assert read_summary_json(run_dir) is None


def test_read_summary_json_round_trip(core_config, isolated_cwd) -> None:
    load_config(core_config)
    measure_value(key="k1", value=3.3)
    run_endex_expect_code(0)
    run_dir = latest_output_dir(isolated_cwd)
    payload = read_summary_json(run_dir)
    assert payload is not None
    assert payload["overall_result"] == "PASS"
    assert payload["exit_code"] == 0
