"""
Profile Colosseum unit tests to find slow paths (stdlib cProfile).

Used by profile_unit_tests.py; importable for ad-hoc analysis.
"""

from __future__ import annotations

import cProfile
import pstats
import time
from collections.abc import Iterable
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

# pstats restriction regex (OR); matches repo packages and unit tests on Win/POSIX
_PROJECT_PATH_RE = r"(colosseum[\\/]|colosseum_equipment|colosseum_shared|tests[\\/]unit)"


@dataclass(frozen=True)
class ProfileReport:
    exit_code: int
    wall_seconds: float
    stats_path: Path | None
    summary_text: str


def _format_stats(
    profiler: cProfile.Profile,
    *,
    sort_key: str,
    limit: int,
    restriction: str | int | None,
    strip_dirs: bool,
) -> str:
    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    if strip_dirs:
        stats.strip_dirs()
    stats.sort_stats(sort_key)
    if restriction is None:
        stats.print_stats(limit)
    else:
        stats.print_stats(restriction, limit)
    return stream.getvalue()


def profile_pytest_unit_tests(
    repo_root: Path,
    *,
    pytest_args: Iterable[str] | None = None,
    sort: str = "cumulative",
    limit: int = 40,
    project_only: bool = True,
    strip_dirs: bool = False,
    save_stats: Path | None = None,
) -> ProfileReport:
    """
    Run pytest on tests/unit under cProfile and return a text summary.

    sort: pstats key, e.g. cumulative, tottime, calls
    """
    import pytest

    _ = repo_root  # reserved for future chdir / path checks
    args = ["tests/unit", "-q", "--durations=15"]
    if pytest_args:
        args.extend(pytest_args)

    profiler = cProfile.Profile()
    started = time.perf_counter()
    profiler.enable()
    try:
        exit_code = pytest.main([*args])
    finally:
        profiler.disable()
    wall = time.perf_counter() - started

    if save_stats is not None:
        save_stats.parent.mkdir(parents=True, exist_ok=True)
        profiler.dump_stats(str(save_stats))

    sections = [
        f"Wall time: {wall:.3f}s",
        f"Pytest exit code: {exit_code}",
        "",
        f"=== Top {limit} by {sort} (all paths) ===",
        _format_stats(
            profiler,
            sort_key=sort,
            limit=limit,
            restriction=None,
            strip_dirs=strip_dirs,
        ),
    ]
    if project_only:
        sections.extend(
            [
                "",
                f"=== Top {limit} by {sort} (project: colosseum*, tests/unit) ===",
                _format_stats(
                    profiler,
                    sort_key=sort,
                    limit=limit,
                    restriction=_PROJECT_PATH_RE,
                    strip_dirs=strip_dirs,
                ),
                "",
                f"=== Top {limit} by tottime (self time, project only) ===",
                _format_stats(
                    profiler,
                    sort_key="tottime",
                    limit=limit,
                    restriction=_PROJECT_PATH_RE,
                    strip_dirs=strip_dirs,
                ),
            ]
        )

    return ProfileReport(
        exit_code=int(exit_code),
        wall_seconds=wall,
        stats_path=save_stats,
        summary_text="\n".join(sections),
    )
