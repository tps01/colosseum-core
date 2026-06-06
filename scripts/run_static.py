#!/usr/bin/env python3
"""Run Colosseum static analysis (ruff, mypy, bandit, vulture)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Delegate to ``tests/static/run_all.py`` with forwarded CLI arguments.

    :returns: Process exit code (``0`` when all static checks pass).
    :rtype: int
    """
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Run static analysis tools")
    parser.parse_known_args()
    runner = root / "tests" / "static" / "run_all.py"
    cmd = [sys.executable, str(runner), *sys.argv[1:]]
    return int(subprocess.run(cmd, cwd=root, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
