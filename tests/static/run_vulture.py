#!/usr/bin/env python3
"""Run vulture dead-code detection on production packages and scripts."""

from __future__ import annotations

import sys
from pathlib import Path

from _common import REPO, SCAN_PATHS, run_tool

_WHITELIST = Path(__file__).resolve().parent / "vulture_whitelist.py"


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "vulture",
        *SCAN_PATHS,
        str(_WHITELIST),
        "--min-confidence",
        "80",
        "--sort-by-size",
    ]
    code = run_tool(cmd, cwd=REPO)
    if code == 0:
        print("STATIC PASS: vulture")
    else:
        print("STATIC FAIL: vulture", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
