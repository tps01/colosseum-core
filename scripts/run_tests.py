#!/usr/bin/env python3
"""Run Colosseum pytest tiers 1–3; optional Tier 4A regression scripts."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# PyVISA-sim is test-only (.[test] extra) and needs Python 3.10+.
_PYTEST_MARKER_ARGS = ["-m", "not visa_sim"] if sys.version_info < (3, 10) else []


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
        help="After pytest, run soak + docgen regression scripts (no hardware)",
    )
    parser.add_argument(
        "--soak-count",
        type=int,
        default=50,
        help="Iterations for sim soak when --regression (default 50)",
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

    soak = subprocess.call(
        [
            sys.executable,
            str(root / "tests" / "regression" / "run_soak_sim.py"),
            "--count",
            str(args.soak_count),
        ],
        cwd=root,
    )
    if soak != 0:
        return soak

    return subprocess.call(
        [sys.executable, str(root / "tests" / "regression" / "run_docgen_check.py")],
        cwd=root,
    )


if __name__ == "__main__":
    raise SystemExit(main())
