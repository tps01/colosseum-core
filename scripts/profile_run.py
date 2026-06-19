#!/usr/bin/env python3
"""
Profile ``colosseum run`` or ``colosseum run-suite`` with cProfile (runtime, not pytest).

Usage (from repo root):
  python scripts/profile_run.py scripts/offline_smoke/run_sim.py --config scripts/offline_smoke/bench.sim.toml
  python scripts/profile_run.py --suite tests/fixtures/suites/smoke.toml --config examples/configs/bench.sim.toml
  python scripts/profile_run.py --tracemalloc scripts/offline_smoke/run_sim.py --config scripts/offline_smoke/bench.sim.toml
  python scripts/profile_run.py --stats build/profile/run.prof examples/test_power_rails.py --config examples/configs/bench.sim.toml
"""

from __future__ import annotations

import argparse
import pstats
import subprocess
import sys
import time
import tracemalloc
from io import StringIO
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_PACKAGES_RE = r"(colosseum[\\/]|colosseum_equipment|colosseum_shared|colosseum_host)"


def _print_pstats(prof_path: Path, *, sort: str, limit: int) -> None:
    stream = StringIO()
    stats = pstats.Stats(str(prof_path), stream=stream)
    stats.sort_stats(sort)
    stats.print_stats(_PACKAGES_RE, limit)
    print(stream.getvalue())


def _run_with_cprofile(
    cli_command: str,
    cli_argv: list[str],
    *,
    stats_path: Path,
    sort: str,
    limit: int,
) -> int:
    cmd = [
        sys.executable,
        "-m",
        "cProfile",
        "-o",
        str(stats_path),
        "-m",
        "colosseum.runner.cli",
        cli_command,
        *cli_argv,
    ]
    print("+", " ".join(cmd))
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=REPO, check=False)
    wall = time.perf_counter() - started
    print(f"Wall time: {wall:.3f}s (exit {proc.returncode})")
    if stats_path.is_file():
        print(f"\n=== Top {limit} by {sort} (project paths) ===")
        _print_pstats(stats_path, sort=sort, limit=limit)
        print(f"\nSaved profile: {stats_path}")
        print("  View: python -m snakeviz", stats_path)
    return proc.returncode


def _run_with_tracemalloc(cli_command: str, cli_argv: list[str]) -> int:
    tracemalloc.start()
    cmd_display = [sys.executable, "-m", "colosseum.runner.cli", cli_command, *cli_argv]
    print("+", " ".join(cmd_display), "(in-process tracemalloc)")
    started = time.perf_counter()
    from colosseum.runner.cli import run_cli

    code = run_cli([cli_command, *cli_argv])
    wall = time.perf_counter() - started
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"Wall time: {wall:.3f}s (exit {code})")
    print(f"Peak traced memory: {peak / (1024 * 1024):.2f} MiB")
    return code


def main(argv: list[str] | None = None) -> int:
    """Profile one ``colosseum run`` or ``run-suite`` invocation.

    :param argv: Optional argument vector (defaults to ``sys.argv[1:]``).
    :type argv: list[str] | None, optional

    :returns: Process exit code from the run.
    :rtype: int
    """
    parser = argparse.ArgumentParser(description="Profile colosseum run or run-suite (runtime)")
    parser.add_argument(
        "--suite",
        action="store_true",
        help="Profile colosseum run-suite instead of run",
    )
    parser.add_argument(
        "--tracemalloc",
        action="store_true",
        help="Print peak traced memory instead of cProfile (no .prof output)",
    )
    parser.add_argument(
        "--stats",
        type=Path,
        default=None,
        help="cProfile output path (default build/profile/run.prof or suite.prof)",
    )
    parser.add_argument(
        "--sort",
        default="cumulative",
        choices=("cumulative", "tottime", "calls", "ncalls"),
        help="pstats sort key when using cProfile (default cumulative)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=40,
        help="Rows in pstats table (default 40)",
    )
    args, cli_argv = parser.parse_known_args(argv)
    if cli_argv and cli_argv[0] == "--":
        cli_argv = cli_argv[1:]
    if not cli_argv:
        print("profile_run.py: missing script or suite path and options", file=sys.stderr)
        return 2

    cli_command = "run-suite" if args.suite else "run"
    if args.tracemalloc:
        return _run_with_tracemalloc(cli_command, cli_argv)

    default_name = "suite.prof" if args.suite else "run.prof"
    stats_path = args.stats or (REPO / "build" / "profile" / default_name)
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    return _run_with_cprofile(
        cli_command,
        cli_argv,
        stats_path=stats_path.resolve(),
        sort=args.sort,
        limit=args.limit,
    )


if __name__ == "__main__":
    raise SystemExit(main())
