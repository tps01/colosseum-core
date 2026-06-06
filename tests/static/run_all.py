#!/usr/bin/env python3
"""Run all static analysis tools in order."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_DIR = Path(__file__).resolve().parent
_TOOLS = ("ruff", "mypy", "bandit", "vulture")


def _run_script(name: str, extra: list[str]) -> int:
    script = _DIR / f"run_{name}.py"
    cmd = [sys.executable, str(script), *extra]
    return int(subprocess.run(cmd, check=False).returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run static analysis tools")
    parser.add_argument(
        "--tool",
        choices=_TOOLS,
        help="Run a single tool (default: all)",
    )
    parser.add_argument("--fix", action="store_true", help="Pass --fix to ruff only")
    args, remainder = parser.parse_known_args(argv)

    tools = (args.tool,) if args.tool else _TOOLS
    for tool in tools:
        extra = remainder.copy()
        if tool == "ruff" and args.fix:
            extra = ["--fix", *extra]
        code = _run_script(tool, extra)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
