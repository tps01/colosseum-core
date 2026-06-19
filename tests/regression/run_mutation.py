#!/usr/bin/env python3
"""
R-MUT-01 (optional): mutation testing on high-traffic core modules.

Requires: pip install -e ".[mutation]"  (cosmic-ray: MIT)

By default this script only prints instructions. Pass --run to execute Cosmic Ray.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPORT_DIR = REPO / "build" / "mutation"
TARGETS = (
    "colosseum/results/aggregation.py",
    "colosseum/config/normalize.py",
    "colosseum/decorators/verification.py",
)
LOCK_FILE = REPORT_DIR / ".cosmic-ray.lock"


def _run_id(targets: tuple[str, ...]) -> str:
    if len(targets) == 1:
        return targets[0].replace("\\", "/").removesuffix(".py").replace("/", "-")
    return "all"


def _paths(run_id: str) -> dict[str, Path]:
    return {
        "config": REPORT_DIR / f"{run_id}.toml",
        "session": REPORT_DIR / f"{run_id}.sqlite",
        "baseline": REPORT_DIR / f"{run_id}-baseline.sqlite",
        "report": REPORT_DIR / f"{run_id}-report.txt",
        "survivors": REPORT_DIR / f"{run_id}-survivors.txt",
        "html": REPORT_DIR / f"{run_id}.html",
    }


def _console_script(name: str) -> str:
    scripts_dir = Path(sys.executable).resolve().parent
    suffixes = (".exe", ".cmd", ".bat", "") if os.name == "nt" else ("",)
    for suffix in suffixes:
        candidate = scripts_dir / f"{name}{suffix}"
        if candidate.exists():
            return str(candidate)
    return name


def _write_config(config_file: Path, targets: tuple[str, ...], timeout: float) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    test_command = " ".join(
        shlex.quote(part)
        for part in (
            sys.executable.replace("\\", "/"),
            "-m",
            "pytest",
            "tests/unit",
            "-q",
            "-x",
        )
    )
    target_list = ", ".join(json.dumps(target) for target in targets)
    config_file.write_text(
        "\n".join(
            [
                "[cosmic-ray]",
                f"module-path = [{target_list}]",
                f"timeout = {timeout}",
                "excluded-modules = []",
                f"test-command = {json.dumps(test_command)}",
                "",
                "[cosmic-ray.distributor]",
                'name = "local"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def _run(cmd: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO, timeout=timeout, text=True)


def _capture(cmd: list[str], path: Path, *, timeout: int) -> subprocess.CompletedProcess[str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        return subprocess.run(
            cmd,
            cwd=REPO,
            stdout=stream,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            text=True,
        )


def _remove_previous_session(paths: dict[str, Path]) -> None:
    for path in paths.values():
        path.unlink(missing_ok=True)


def _acquire_mutation_lock() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        details = LOCK_FILE.read_text(encoding="utf-8").strip()
        raise RuntimeError(
            f"another mutation run appears to be active ({LOCK_FILE}: {details}). "
            "Cosmic Ray mutates files in the working tree; run mutation jobs serially."
        ) from exc
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(f"pid={os.getpid()}\n")
    return fd


def _release_mutation_lock() -> None:
    LOCK_FILE.unlink(missing_ok=True)


def _mutation_summary(session_file: Path) -> tuple[int, int, int, int, int] | None:
    """Return ``(survived, incomplete, bad_worker, killed, total)`` or ``None``."""
    cosmic_ray = _console_script("cosmic-ray")
    proc = subprocess.run(
        [cosmic_ray, "dump", str(session_file)],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        return None

    survived = 0
    incomplete = 0
    bad_worker = 0
    killed = 0
    parsed = 0
    for line in proc.stdout.splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, list) or len(item) != 2 or item[1] is None:
            continue
        result = item[1]
        if not isinstance(result, dict):
            continue
        parsed += 1
        test_outcome = result.get("test_outcome")
        worker_outcome = result.get("worker_outcome")
        if test_outcome == "survived":
            survived += 1
        elif test_outcome == "killed":
            killed += 1
        if test_outcome in {None, "incompetent"}:
            incomplete += 1
        if worker_outcome not in {None, "normal"}:
            bad_worker += 1
    if parsed == 0:
        return None
    return survived, incomplete, bad_worker, killed, parsed


def verify_mutation_reports(*, target: str | None) -> int:
    """Assert existing Cosmic Ray session reports pass R-MUT-01 gates.

    :param target: One configured target path, or ``None`` for all configured targets.
    :type target: str | None

    :returns: Process exit code (``0`` on success).
    :rtype: int
    """
    try:
        import cosmic_ray  # noqa: F401
    except ImportError:
        print('cosmic-ray is not installed. Run: pip install -e ".[mutation]"', file=sys.stderr)
        return 2

    selected_targets = (target,) if target else TARGETS
    paths = _paths(_run_id(selected_targets))
    session_file = paths["session"]
    if not session_file.is_file():
        print(f"MUTATION FAIL: missing session file {session_file}", file=sys.stderr)
        print("Run Cosmic Ray first or download CI mutation artifacts.", file=sys.stderr)
        return 1

    summary = _mutation_summary(session_file)
    if summary is None:
        print("MUTATION FAIL: could not parse Cosmic Ray dump", file=sys.stderr)
        print(f"Report: {paths['report']}", file=sys.stderr)
        return 1

    survived, incomplete, bad_worker, killed, total = summary
    score = (100.0 * killed / total) if total else 0.0
    print(f"Mutation score: {score:.1f}% ({killed}/{total} killed)")

    if survived or incomplete or bad_worker:
        print(
            "MUTATION FAIL: "
            f"survived={survived}, incomplete={incomplete}, worker_errors={bad_worker}",
            file=sys.stderr,
        )
        print(f"Report:    {paths['report']}", file=sys.stderr)
        print(f"Survivors: {paths['survivors']}", file=sys.stderr)
        if paths["html"].is_file():
            print(f"HTML:      {paths['html']}", file=sys.stderr)
        return 1

    print(f"Report: {paths['report']}")
    if paths["html"].is_file():
        print(f"HTML:   {paths['html']}")
    print("MUTATION PASS: existing reports meet configured targets")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Optional Cosmic Ray driver for Colosseum core")
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute Cosmic Ray (otherwise print instructions only)",
    )
    parser.add_argument(
        "--target",
        choices=TARGETS,
        help="Run one configured target instead of all configured targets",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Cosmic Ray per-mutant test timeout in seconds (default 10)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Skip Cosmic Ray run; assert pass/fail from existing build/mutation/ reports",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip the unit-test preflight before mutation testing",
    )
    args = parser.parse_args(argv)

    if args.verify_only:
        return verify_mutation_reports(target=args.target)

    if not args.run:
        print("Mutation testing is optional for Colosseum regression.")
        print('Install: pip install -e ".[mutation]"')
        print("Run:     python tests/regression/run_mutation.py --run")
        print("Single:  python tests/regression/run_mutation.py --run --target", TARGETS[0])
        print("Verify:  python tests/regression/run_mutation.py --verify-only --target", TARGETS[0])
        print("Profile: python scripts/profile_tests.py --tier unit  (speed up unit tests first)")
        print("Reports: build/mutation/<target>-report.txt")
        print("Targets:", ", ".join(TARGETS))
        return 0

    try:
        import cosmic_ray  # noqa: F401
    except ImportError:
        print('cosmic-ray is not installed. Run: pip install -e ".[mutation]"', file=sys.stderr)
        return 2

    try:
        _acquire_mutation_lock()
    except RuntimeError as exc:
        print(f"MUTATION ABORT: {exc}", file=sys.stderr)
        return 2

    try:
        if not args.skip_preflight:
            preflight = _run(
                [sys.executable, "-m", "pytest", "tests/unit", "-q"],
                timeout=300,
            )
            if preflight.returncode != 0:
                print("MUTATION ABORT: unit-test preflight failed", file=sys.stderr)
                return preflight.returncode

        selected_targets = (args.target,) if args.target else TARGETS
        paths = _paths(_run_id(selected_targets))
        _remove_previous_session(paths)
        _write_config(paths["config"], selected_targets, args.timeout)

        cosmic_ray = _console_script("cosmic-ray")
        cr_report = _console_script("cr-report")
        cr_html = _console_script("cr-html")

        init = _run([cosmic_ray, "init", str(paths["config"]), str(paths["session"])], timeout=300)
        if init.returncode != 0:
            print("MUTATION ABORT: Cosmic Ray init failed", file=sys.stderr)
            return init.returncode

        baseline = _run(
            [cosmic_ray, "baseline", "--session-file", str(paths["baseline"]), str(paths["config"])],
            timeout=300,
        )
        if baseline.returncode != 0:
            print("MUTATION ABORT: Cosmic Ray baseline failed", file=sys.stderr)
            return baseline.returncode

        exec_result = _run([cosmic_ray, "exec", str(paths["config"]), str(paths["session"])], timeout=3600)
        _capture([cr_report, str(paths["session"]), "--show-pending"], paths["report"], timeout=120)
        _capture(
            [cr_report, str(paths["session"]), "--surviving-only", "--show-diff"],
            paths["survivors"],
            timeout=120,
        )
        _capture([cr_html, str(paths["session"])], paths["html"], timeout=120)

        if exec_result.returncode != 0:
            print("MUTATION FAIL: Cosmic Ray execution failed", file=sys.stderr)
            print(f"Report: {paths['report']}", file=sys.stderr)
            return exec_result.returncode

        summary = _mutation_summary(paths["session"])
        if summary is None:
            print("MUTATION WARN: could not parse Cosmic Ray dump; review report manually")
            print(f"Report: {paths['report']}")
            return 0

        survived, incomplete, bad_worker, killed, total = summary
        score = (100.0 * killed / total) if total else 0.0
        print(f"Mutation score: {score:.1f}% ({killed}/{total} killed)")
        if survived or incomplete or bad_worker:
            print(
                "MUTATION FAIL: "
                f"survived={survived}, incomplete={incomplete}, worker_errors={bad_worker}",
                file=sys.stderr,
            )
            print(f"Report:    {paths['report']}", file=sys.stderr)
            print(f"Survivors: {paths['survivors']}", file=sys.stderr)
            print(f"HTML:      {paths['html']}", file=sys.stderr)
            return 1

        print(f"Report: {paths['report']}")
        print(f"HTML:   {paths['html']}")
        print("MUTATION PASS: Cosmic Ray completed for configured targets")
        return 0
    finally:
        _release_mutation_lock()


if __name__ == "__main__":
    raise SystemExit(main())
