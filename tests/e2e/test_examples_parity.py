"""E2E: examples/ scripts via CLI (sim bench)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _run_example(name: str, bench_sim: Path, isolated_cwd: Path, env: dict[str, str]) -> int:
    script = REPO / "examples" / name
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "colosseum.runner.cli",
            "run",
            str(script),
            "--config",
            str(bench_sim),
        ],
        cwd=isolated_cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise AssertionError(f"{name} failed: {proc.stderr}\n{proc.stdout}")
    return proc.returncode


def test_example_power_rails(bench_sim, isolated_cwd, subprocess_env) -> None:
    env = dict(subprocess_env)
    env.pop("COLOSSEUM_BENCH_CONFIG", None)
    _run_example("test_power_rails.py", bench_sim, isolated_cwd, env)


def test_example_ssh_health(bench_sim, isolated_cwd, subprocess_env) -> None:
    _run_example("test_ssh_health.py", bench_sim, isolated_cwd, subprocess_env)
