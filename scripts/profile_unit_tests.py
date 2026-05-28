#!/usr/bin/env python3
"""
Profile unit test execution time (cProfile + pytest --durations).

Use this to find slow tests and hot paths before mutation testing or CI tuning.

Usage (from repo root):
  python scripts/profile_unit_tests.py
  python scripts/profile_unit_tests.py --limit 60 --sort tottime
  python scripts/profile_unit_tests.py --stats build/profile/unit_tests.prof
  python scripts/profile_unit_tests.py --all-paths
  python scripts/profile_unit_tests.py -k test_aggregation
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from unit_test_profiler import profile_pytest_unit_tests  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Profile Colosseum tests/unit with cProfile",
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
        help="Write raw .prof for snakeviz: python -m snakeviz <file>",
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
        help="Extra pytest args (e.g. -k name, tests/unit/test_foo.py)",
    )
    args = parser.parse_args(argv)

    extra = list(args.pytest_args)
    if extra and extra[0] == "--":
        extra = extra[1:]

    report = profile_pytest_unit_tests(
        root,
        pytest_args=extra or None,
        sort=args.sort,
        limit=args.limit,
        project_only=not args.all_paths,
        strip_dirs=args.strip_dirs,
        save_stats=args.stats.resolve() if args.stats else None,
    )
    print(report.summary_text)
    if report.stats_path is not None:
        print(f"\nSaved profile: {report.stats_path}")
        print("  View: python -m snakeviz", report.stats_path)
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
