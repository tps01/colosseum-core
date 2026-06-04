"""E2E-W1-02: direct Python execution matches CLI artifact contract."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tests.support.helpers import latest_output_dir, verification_row

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tests" / "fixtures" / "scripts" / "optional_fail_test.py"


def test_direct_python_optional_fail_exits_zero(bench_sim, isolated_cwd, subprocess_env) -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=isolated_cwd,
        env=subprocess_env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    run_dir = latest_output_dir(isolated_cwd)
    assert (run_dir / "execution.sqlite").is_file()
    assert verification_row(run_dir, "probe_optional")[0] == "FAIL"
    assert verification_row(run_dir, "vrail_3v3")[0] == "PASS"
