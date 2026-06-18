#!/usr/bin/env python3
"""Run bandit on production packages and scripts."""

from __future__ import annotations

import sys

from _common import REPO, SCAN_PATHS, run_tool


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "bandit",
        "-r",
        *SCAN_PATHS,
        "-c",
        "pyproject.toml",
        "-ll",
    ]
    code = run_tool(cmd, cwd=REPO)
    if code == 0:
        print("STATIC PASS: bandit")
    else:
        print("STATIC FAIL: bandit", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
