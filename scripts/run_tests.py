#!/usr/bin/env python3
"""Run Colosseum pytest tiers 1–3; optional Tier 4A regression scripts."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# PyVISA-sim is test-only (.[test] extra) and needs Python 3.10+.
_PYTEST_MARKER_ARGS = ["-m", "not visa_sim"] if sys.version_info < (3, 10) else []

_REGRESSION_DIR = Path(__file__).resolve().parents[1] / "tests" / "regression"


def _run_regression_script(name: str, *extra: str) -> int:
    root = Path(__file__).resolve().parents[1]
    cmd = [sys.executable, str(_REGRESSION_DIR / name), *extra]
    return int(subprocess.call(cmd, cwd=root))


def main() -> int:
    """Run pytest tiers 1–3 and optionally Tier 4A regression scripts.

    :returns: Process exit code (``0`` on success).
    :rtype: int
    """
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Run Colosseum test tiers")
    parser.add_argument(
        "--regression",
        action="store_true",
        help="After pytest, run Tier 4A scripts: soak, docgen, offline bundle",
    )
    parser.add_argument(
        "--skip-offline",
        action="store_true",
        help="With --regression, skip R-OFFLINE-00 (offline bundle is slow; CI runs it separately)",
    )
    parser.add_argument(
        "--soak-count",
        type=int,
        default=10,
        help="Iterations for sim soak when --regression (default 10; CI soak job uses 5)",
    )
    args, pytest_argv = parser.parse_known_args()
    if pytest_argv and pytest_argv[0] == "--":
        pytest_argv = pytest_argv[1:]

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit",
        "tests/integration",
        "tests/e2e",
        "-q",
        *_PYTEST_MARKER_ARGS,
        *pytest_argv,
    ]
    code = subprocess.call(cmd, cwd=root)
    if code != 0:
        return code

    if not args.regression:
        return 0

    for script, extra in (
        ("run_soak_sim.py", ("--count", str(args.soak_count))),
        ("run_docgen_check.py", ()),
    ):
        code = _run_regression_script(script, *extra)
        if code != 0:
            return code

    if args.skip_offline:
        return 0

    return _run_regression_script("run_offline_install_check.py")


if __name__ == "__main__":
    raise SystemExit(main())
