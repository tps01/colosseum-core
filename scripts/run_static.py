#!/usr/bin/env python3
"""Run Colosseum static analysis (ruff, mypy, bandit, vulture)."""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable


def main() -> int:
    """Delegate to ``tests/static/run_all.py`` with forwarded CLI arguments.

    :returns: Process exit code (``0`` when all static checks pass).
    :rtype: int
    """
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Run static analysis tools")
    parser.parse_known_args()
    runner_dir = root / "tests" / "static"
    runner = runner_dir / "run_all.py"
    sys.path.insert(0, str(runner_dir))
    os.chdir(root)
    spec = importlib.util.spec_from_file_location("colosseum_static_run_all", runner)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load static runner: {runner}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run_all = cast("Callable[[list[str]], int]", module.main)
    return run_all(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
