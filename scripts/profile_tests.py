#!/usr/bin/env python3
"""
Profile pytest tiers with cProfile + pytest --durations.

Use to find slow tests and hot paths before CI tuning.

Usage (from repo root):
  python scripts/profile_tests.py --tier unit
  python scripts/profile_tests.py --tier integration --sort tottime
  python scripts/profile_tests.py --tier all --stats build/profile/all.prof
  python scripts/profile_tests.py --tier unit -k test_aggregation
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from pytest_profiler import profile_pytest  # noqa: E402

_TIER_PATHS: dict[str, tuple[str, ...]] = {
    "unit": ("tests/unit",),
    "integration": ("tests/integration",),
    "e2e": ("tests/e2e",),
    "all": ("tests/unit", "tests/integration", "tests/e2e"),
}

def main(argv: list[str] | None = None) -> int:
    """Profile selected pytest tier(s) with cProfile and print timing tables.

    :param argv: Optional argument vector (defaults to ``sys.argv[1:]``).
    :type argv: list[str] | None, optional

    :returns: Pytest exit code from the profiled run.
    :rtype: int
    """
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Profile Colosseum pytest tiers with cProfile")
    parser.add_argument(
        "--tier",
        choices=sorted(_TIER_PATHS),
        default="unit",
        help="Pytest tier to profile (default unit)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=40,
        help="Number of rows per stats table (default 40)",
    )
    parser.add_argument(
        "--sort",
        default="cumulative",
        choices=("cumulative", "tottime", "calls", "ncalls"),
        help="Primary pstats sort key (default cumulative)",
    )
    parser.add_argument(
        "--stats",
        type=Path,
        default=None,
        help="Write raw .prof for snakeviz (default: build/profile/<tier>.prof when omitted)",
    )
    parser.add_argument(
        "--all-paths",
        action="store_true",
        help="Omit project-only tables (still prints one global table)",
    )
    parser.add_argument(
        "--strip-dirs",
        action="store_true",
        help="Strip path prefixes in pstats (shorter output; harder to read on editable installs)",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Extra pytest args after -- (e.g. -- -k name tests/unit/test_foo.py)",
    )
    args = parser.parse_args(argv)

    extra = list(args.pytest_args)
    if extra and extra[0] == "--":
        extra = extra[1:]

    stats_path = args.stats
    if stats_path is None:
        stats_path = root / "build" / "profile" / f"{args.tier}.prof"

    report = profile_pytest(
        root,
        _TIER_PATHS[args.tier],
        pytest_args=extra or None,
        sort=args.sort,
        limit=args.limit,
        project_only=not args.all_paths,
        strip_dirs=args.strip_dirs,
        save_stats=stats_path.resolve(),
    )
    print(report.summary_text)
    if report.stats_path is not None:
        print(f"\nSaved profile: {report.stats_path}")
        print("  View: python -m snakeviz", report.stats_path)
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
