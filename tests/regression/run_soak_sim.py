#!/usr/bin/env python3
"""
R-SOAK-01: repeat suite runs on sim bench (resource / stability check).

Usage (from repo root):
  python tests/regression/run_soak_sim.py
  python tests/regression/run_soak_sim.py --count 10
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SUITE = REPO / "tests" / "fixtures" / "suites" / "happy.toml"
BENCH = REPO / "examples" / "configs" / "bench.sim.toml"
FAIL_PATTERNS = (
    "Traceback",
    "TransportError",
    "paramiko",
    "VISA",
    "SerialException",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sim soak: repeated run-suite")
    parser.add_argument("--count", type=int, default=50, help="Iterations (default 50)")
    parser.add_argument("--suite", type=Path, default=SUITE)
    parser.add_argument("--config", type=Path, default=BENCH)
    args = parser.parse_args(argv)

    if not args.suite.is_file():
        print(f"Suite not found: {args.suite}", file=sys.stderr)
        return 2
    if not args.config.is_file():
        print(f"Config not found: {args.config}", file=sys.stderr)
        return 2

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO)

    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="colosseum_soak_") as tmp:
        cwd = Path(tmp)
        for i in range(args.count):
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "colosseum.runner.cli",
                    "run-suite",
                    str(args.suite.resolve()),
                    "--config",
                    str(args.config.resolve()),
                ],
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=180,
            )
            if proc.returncode != 0:
                failures.append(f"iter {i + 1}: exit {proc.returncode}\n{proc.stderr[-500:]}")
                continue
            outputs = cwd / "outputs"
            if not outputs.is_dir():
                failures.append(f"iter {i + 1}: no outputs/ directory")
                continue
            runs = sorted(outputs.glob("*"), key=lambda p: p.stat().st_mtime)
            log_path = runs[-1] / "debug.log"
            if log_path.is_file():
                log_text = log_path.read_text(encoding="utf-8", errors="replace")
                for pattern in FAIL_PATTERNS:
                    if pattern in log_text:
                        failures.append(f"iter {i + 1}: log contains `{pattern}`")

    if failures:
        print(f"SOAK FAIL: {len(failures)} issue(s) in {args.count} runs", file=sys.stderr)
        for item in failures[:10]:
            print(item, file=sys.stderr)
        if len(failures) > 10:
            print(f"... and {len(failures) - 10} more", file=sys.stderr)
        return 1

    print(f"SOAK PASS: {args.count} run-suite iterations on sim bench")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
