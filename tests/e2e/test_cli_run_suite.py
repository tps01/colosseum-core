"""E2E-W3: colosseum run-suite via subprocess."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.helpers import latest_output_dir, query_db

from tests.support.helpers import REPO_ROOT as REPO


def _cli_run_suite(suite: Path, config: Path, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "colosseum.runner.cli",
            "run-suite",
            str(suite),
            "--config",
            str(config),
        ],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


@pytest.mark.requirement("E2E-W3-01")
def test_run_suite_fixture_happy(core_config, fixtures_dir, isolated_cwd, subprocess_env) -> None:
    suite = fixtures_dir / "suites" / "happy.toml"
    proc = _cli_run_suite(suite, core_config, isolated_cwd, subprocess_env)
    assert proc.returncode == 0, proc.stderr
    run_dir = latest_output_dir(isolated_cwd)
    summary = (run_dir / "summary.txt").read_text(encoding="utf-8")
    assert "fixture_happy" in summary or "Overall result: PASS" in summary
    assert (run_dir / "execution.sqlite").is_file()
    meas_count = query_db(run_dir, "SELECT COUNT(*) FROM measurements")[0][0]
    assert meas_count == 0  # pass_test is a no-op; suite still succeeds


@pytest.mark.requirement("E2E-W3-01")
def test_run_suite_smoke_core_api(core_config, fixtures_dir, isolated_cwd, subprocess_env) -> None:
    suite = fixtures_dir / "suites" / "smoke.toml"
    proc = _cli_run_suite(suite, core_config, isolated_cwd, subprocess_env)
    assert proc.returncode == 0, proc.stderr
    run_dir = latest_output_dir(isolated_cwd)
    domains = {
        row[0]
        for row in query_db(run_dir, "SELECT DISTINCT domain FROM measurements")
    }
    assert domains == {"core"}
    summary = (run_dir / "summary.txt").read_text(encoding="utf-8")
    assert "Overall result: PASS" in summary


def test_run_suite_setup_fail_exits_one(core_config, fixtures_dir, isolated_cwd, subprocess_env) -> None:
    suite = fixtures_dir / "suites" / "setup_fail.toml"
    proc = _cli_run_suite(suite, core_config, isolated_cwd, subprocess_env)
    assert proc.returncode == 1, proc.stderr
    run_dir = latest_output_dir(isolated_cwd)
    assert (run_dir / "summary.txt").is_file()
    starts = "\n".join(m[0] for m in query_db(run_dir, "SELECT message FROM events WHERE message LIKE 'script_start:%'"))
    assert "pass_test.py" not in starts


def test_run_suite_bad_config_exits_one(fixtures_dir, isolated_cwd, subprocess_env) -> None:
    config = isolated_cwd / "bad.toml"
    config.write_text(
        "[runtime\n"
        "label = \"broken\"\n",
        encoding="utf-8",
    )
    suite = fixtures_dir / "suites" / "happy.toml"
    proc = _cli_run_suite(suite, config, isolated_cwd, subprocess_env)
    assert proc.returncode == 1
