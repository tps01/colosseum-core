"""E2E-W1/W2: colosseum run via subprocess."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import latest_output_dir, query_db, verification_row

REPO = Path(__file__).resolve().parents[2]


def _cli_run(
    script: Path,
    config: Path,
    cwd: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "colosseum.runner.cli",
            "run",
            str(script),
            "--config",
            str(config),
        ],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.requirement("E2E-W1-01")
def test_cli_run_power_rails(bench_sim, isolated_cwd, subprocess_env) -> None:
    script = REPO / "examples" / "test_power_rails.py"
    proc = _cli_run(script, bench_sim, isolated_cwd, subprocess_env)
    assert proc.returncode == 0, proc.stderr
    run_dir = latest_output_dir(isolated_cwd)
    opt = verification_row(run_dir, "engineering_probe_point")
    assert opt is not None and opt[0] == "FAIL" and opt[1] == 1
    req = verification_row(run_dir, "vrail_3v3")
    assert req is not None and req[0] == "PASS"


@pytest.mark.requirement("E2E-W1-03")
def test_cli_run_missing_measurement_exits_one(bench_sim, isolated_cwd, subprocess_env) -> None:
    script = REPO / "tests" / "fixtures" / "scripts" / "fail_required_verify.py"
    proc = _cli_run(script, bench_sim, isolated_cwd, subprocess_env)
    assert proc.returncode == 1, proc.stderr
    run_dir = latest_output_dir(isolated_cwd)
    row = verification_row(run_dir, "vrail_3v3")
    assert row is not None and row[0] == "ERROR"


@pytest.mark.requirement("E2E-W1-04")
def test_cli_optional_fail_exits_zero(bench_sim, isolated_cwd, subprocess_env) -> None:
    script = REPO / "tests" / "fixtures" / "scripts" / "optional_fail_test.py"
    proc = _cli_run(script, bench_sim, isolated_cwd, subprocess_env)
    assert proc.returncode == 0, proc.stderr
    run_dir = latest_output_dir(isolated_cwd)
    assert verification_row(run_dir, "probe_optional")[0] == "FAIL"
    assert verification_row(run_dir, "vrail_3v3")[0] == "PASS"


@pytest.mark.requirement("E2E-W2-02")
def test_cli_run_ssh_health(bench_sim, isolated_cwd, subprocess_env) -> None:
    script = REPO / "examples" / "test_ssh_health.py"
    proc = _cli_run(script, bench_sim, isolated_cwd, subprocess_env)
    assert proc.returncode == 0, proc.stderr
    run_dir = latest_output_dir(isolated_cwd)
    assert verification_row(run_dir, "uut_version")[0] == "PASS"
