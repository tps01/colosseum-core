#!/usr/bin/env python3
"""Summarize GitHub Actions job durations from recent workflow runs."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def _run_gh(args: list[str]) -> str:
    """Run ``gh`` and return stdout.

    :param args: Arguments after ``gh``.
    :type args: list[str]

    :returns: Command stdout.
    :rtype: str

    :raises SystemExit: When ``gh`` is missing or the command fails.
    """
    try:
        proc = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            "gh CLI not found; install from https://cli.github.com/ and run gh auth login"
        ) from exc
    if proc.returncode != 0:
        msg = proc.stderr.strip() or proc.stdout.strip() or "gh command failed"
        raise SystemExit(msg)
    return proc.stdout


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _duration_seconds(started: str | None, completed: str | None) -> float | None:
    start = _parse_ts(started)
    end = _parse_ts(completed)
    if start is None or end is None:
        return None
    return max(0.0, (end - start).total_seconds())


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (pct / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _fetch_runs(*, workflow: str, limit: int, conclusion: str | None) -> list[dict]:
    args = [
        "run",
        "list",
        f"--workflow={workflow}",
        f"--limit={limit}",
        "--json",
        "databaseId,conclusion,createdAt,updatedAt,displayTitle,event",
    ]
    if conclusion:
        args.append(f"--{conclusion}")
    payload = json.loads(_run_gh(args))
    return payload if isinstance(payload, list) else []


def _fetch_jobs(run_id: int) -> list[dict]:
    payload = json.loads(_run_gh(["run", "view", str(run_id), "--json", "jobs"]))
    jobs = payload.get("jobs", [])
    return jobs if isinstance(jobs, list) else []


def collect_step_durations(*, run_id: int) -> dict[str, list[tuple[str, float]]]:
    """Return per-job step durations for one workflow run.

    :param run_id: GitHub Actions run database ID.
    :type run_id: int

    :returns: ``job_name -> [(step_name, seconds), ...]``.
    :rtype: dict[str, list[tuple[str, float]]]
    """
    result: dict[str, list[tuple[str, float]]] = {}
    for job in _fetch_jobs(run_id):
        job_name = str(job.get("name", "unknown"))
        steps: list[tuple[str, float]] = []
        for step in job.get("steps", []):
            if not isinstance(step, dict):
                continue
            seconds = _duration_seconds(step.get("startedAt"), step.get("completedAt"))
            if seconds is None:
                continue
            steps.append((str(step.get("name", "unknown")), seconds))
        if steps:
            result[job_name] = steps
    return result


def _print_step_report(*, run_id: int, job_filter: str | None) -> None:
    steps_by_job = collect_step_durations(run_id=run_id)
    if not steps_by_job:
        print(f"No step timing data for run {run_id}.", file=sys.stderr)
        return
    print(f"Run {run_id} step timings (seconds)")
    print("")
    for job_name, steps in sorted(steps_by_job.items()):
        if job_filter and job_filter.lower() not in job_name.lower():
            continue
        print(job_name)
        for step_name, seconds in steps:
            print(f"  {step_name:<40} {seconds:7.1f}s")
        print("")


def collect_job_durations(
    *,
    workflow: str,
    limit: int,
    conclusion: str | None,
) -> tuple[list[dict], dict[str, list[float]]]:
    """Fetch runs and aggregate per-job durations in seconds.

    :param workflow: Workflow file name (e.g. ``ci.yml``).
    :type workflow: str
    :param limit: Number of recent runs to inspect.
    :type limit: int
    :param conclusion: Optional gh filter (``success``, ``failure``).
    :type conclusion: str | None

    :returns: ``(run_rows, job_name -> [durations])``.
    :rtype: tuple[list[dict], dict[str, list[float]]]
    """
    runs = _fetch_runs(workflow=workflow, limit=limit, conclusion=conclusion)
    run_rows: list[dict] = []
    by_job: dict[str, list[float]] = defaultdict(list)

    for run in runs:
        run_id = int(run["databaseId"])
        jobs = _fetch_jobs(run_id)
        job_durations: list[float] = []
        for job in jobs:
            seconds = _duration_seconds(job.get("startedAt"), job.get("completedAt"))
            if seconds is None:
                continue
            name = str(job.get("name", "unknown"))
            by_job[name].append(seconds)
            job_durations.append(seconds)
        run_rows.append(
            {
                "run_id": run_id,
                "conclusion": run.get("conclusion"),
                "created_at": run.get("createdAt"),
                "billable_seconds": sum(job_durations),
                "wall_seconds": max(job_durations) if job_durations else 0.0,
                "job_count": len(jobs),
            }
        )
    return run_rows, by_job


def _rank_jobs(by_job: dict[str, list[float]]) -> list[dict]:
    rows: list[dict] = []
    for name, durations in by_job.items():
        rows.append(
            {
                "job": name,
                "samples": len(durations),
                "median_s": statistics.median(durations),
                "p90_s": _percentile(durations, 90.0),
                "max_s": max(durations),
            }
        )
    rows.sort(key=lambda row: row["median_s"], reverse=True)
    return rows


def _write_markdown(
    *,
    path: Path,
    workflow: str,
    run_rows: list[dict],
    ranked: list[dict],
) -> None:
    lines = [
        f"# GitHub Actions timing summary ({workflow})",
        "",
        f"Runs analyzed: {len(run_rows)}",
        "",
        "## Per-job duration (seconds)",
        "",
        "| Job | Samples | Median | P90 | Max |",
        "|-----|---------|--------|-----|-----|",
    ]
    for row in ranked:
        lines.append(
            f"| {row['job']} | {row['samples']} | {row['median_s']:.1f} | "
            f"{row['p90_s']:.1f} | {row['max_s']:.1f} |"
        )
    lines.extend(
        [
            "",
            "## Per-run billable time",
            "",
            "| Run ID | Conclusion | Billable (s) | Wall (s) | Jobs |",
            "|--------|------------|--------------|----------|------|",
        ]
    )
    for row in run_rows:
        lines.append(
            f"| {row['run_id']} | {row['conclusion']} | {row['billable_seconds']:.1f} | "
            f"{row['wall_seconds']:.1f} | {row['job_count']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_csv(path: Path, ranked: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["job", "samples", "median_s", "p90_s", "max_s"],
        )
        writer.writeheader()
        for row in ranked:
            writer.writerow(
                {
                    "job": row["job"],
                    "samples": row["samples"],
                    "median_s": f"{row['median_s']:.1f}",
                    "p90_s": f"{row['p90_s']:.1f}",
                    "max_s": f"{row['max_s']:.1f}",
                }
            )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for workflow run duration summaries.

    :param argv: Optional argument vector (defaults to ``sys.argv[1:]``).
    :type argv: list[str] | None, optional

    :returns: Process exit code (``0`` on success).
    :rtype: int
    """
    parser = argparse.ArgumentParser(description="Summarize GitHub Actions job durations")
    parser.add_argument(
        "--workflow",
        default="ci.yml",
        help="Workflow file name (default: ci.yml)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of recent runs to analyze (default: 20)",
    )
    parser.add_argument(
        "--conclusion",
        choices=("success", "failure"),
        help="Filter runs by conclusion (default: all)",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        help="Write Markdown report to this path",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="Write CSV job ranking to this path",
    )
    parser.add_argument(
        "--run-id",
        type=int,
        help="Print per-step timings for a single workflow run",
    )
    parser.add_argument(
        "--job-filter",
        help="With --run-id, only show jobs whose name contains this substring",
    )
    args = parser.parse_args(argv)

    if args.run_id is not None:
        _print_step_report(run_id=args.run_id, job_filter=args.job_filter)
        return 0

    run_rows, by_job = collect_job_durations(
        workflow=args.workflow,
        limit=args.limit,
        conclusion=args.conclusion,
    )
    if not by_job:
        print("No job timing data found.", file=sys.stderr)
        return 1

    ranked = _rank_jobs(by_job)
    print(f"Workflow: {args.workflow} ({len(run_rows)} runs)")
    print("")
    print(f"{'Job':<45} {'N':>4} {'Median':>8} {'P90':>8} {'Max':>8}")
    for row in ranked:
        print(
            f"{row['job']:<45} {row['samples']:>4} "
            f"{row['median_s']:>7.1f}s {row['p90_s']:>7.1f}s {row['max_s']:>7.1f}s"
        )

    if args.markdown:
        _write_markdown(
            path=args.markdown,
            workflow=args.workflow,
            run_rows=run_rows,
            ranked=ranked,
        )
        print(f"\nWrote Markdown: {args.markdown}")
    if args.csv:
        _write_csv(args.csv, ranked)
        print(f"Wrote CSV: {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
