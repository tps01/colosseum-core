"""I-SUITE: run_suite phase behavior."""

from __future__ import annotations

import pytest

from colosseum.runner.suite import run_suite
from tests.support.helpers import latest_output_dir, query_db


def _run_suite_expect_exit(suite_path, core_config, isolated_cwd, code: int) -> None:
    with pytest.raises(SystemExit) as exc:
        run_suite(suite_path, core_config)
    assert exc.value.code == code


def test_happy_suite_single_output_db_and_summary(fixtures_dir, core_config, isolated_cwd) -> None:
    suite = fixtures_dir / "suites" / "happy.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 0)
    run_dir = latest_output_dir(isolated_cwd)
    assert (run_dir / "summary.txt").is_file()
    phases = {row[0] for row in query_db(run_dir, "SELECT message FROM events WHERE message LIKE 'phase_enter:%'")}
    assert "phase_enter:setup" in phases
    assert "phase_enter:test" in phases
    assert "phase_enter:teardown" in phases


def test_setup_failure_skips_tests_but_runs_teardown(fixtures_dir, core_config, isolated_cwd) -> None:
    suite = fixtures_dir / "suites" / "setup_fail.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 1)
    run_dir = latest_output_dir(isolated_cwd)
    starts = query_db(run_dir, "SELECT message FROM events WHERE message LIKE 'script_start:%'")
    started = "\n".join(m[0] for m in starts)
    assert "setup_fail.py" in started
    assert "pass_test.py" not in started
    assert "teardown_ok.py" in started
    summary = (run_dir / "summary.txt").read_text(encoding="utf-8")
    assert "FAIL" in summary


def test_teardown_failure_fails_run_even_when_tests_pass(fixtures_dir, core_config, isolated_cwd) -> None:
    suite = fixtures_dir / "suites" / "teardown_fail.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 1)
    run_dir = latest_output_dir(isolated_cwd)
    meta = dict(query_db(run_dir, "SELECT key, value FROM run_metadata"))
    assert meta.get("exit_code") == "1"


def test_test_script_exception_fails_suite_without_verification(
    fixtures_dir, core_config, isolated_cwd
) -> None:
    suite = fixtures_dir / "suites" / "test_script_crash.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 1)
    run_dir = latest_output_dir(isolated_cwd)
    errors = query_db(run_dir, "SELECT message FROM events WHERE message LIKE 'script_fail:%'")
    assert errors, "expected script_fail event for crashed test"
    summary = (run_dir / "summary.txt").read_text(encoding="utf-8")
    assert "Overall result: FAIL" in summary
