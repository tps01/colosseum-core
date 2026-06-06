#!/usr/bin/env python3
"""Run mypy on production packages and scripts."""

from __future__ import annotations

import sys

from _common import REPO, SCAN_PATHS, run_tool


def main() -> int:
    cmd = [sys.executable, "-m", "mypy", *SCAN_PATHS]
    code = run_tool(cmd, cwd=REPO)
    if code == 0:
        print("STATIC PASS: mypy")
    else:
        print("STATIC FAIL: mypy", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
