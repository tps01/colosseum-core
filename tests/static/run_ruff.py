#!/usr/bin/env python3
"""Run ruff on production packages and scripts."""

from __future__ import annotations

import argparse
import sys

from _common import REPO, SCAN_PATHS, run_tool


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ruff lint (production scope)")
    parser.add_argument("--fix", action="store_true", help="Apply safe auto-fixes")
    args = parser.parse_args(argv)

    cmd = [sys.executable, "-m", "ruff", "check", *SCAN_PATHS]
    if args.fix:
        cmd.append("--fix")
    code = run_tool(cmd, cwd=REPO)
    if code == 0:
        print("STATIC PASS: ruff")
    else:
        print("STATIC FAIL: ruff", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
