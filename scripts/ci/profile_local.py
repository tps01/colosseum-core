#!/usr/bin/env python3
"""Mirror GitHub Actions CI job commands locally with wall-clock timing."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCGEN = REPO / "scripts" / "docgen" / "build_all.py"


def _run_step(label: str, cmd: Sequence[str], *, cwd: Path | None = None) -> int:
    print(f"\n== {label} ==")
    print("+", " ".join(cmd))
    start = time.monotonic()
    proc = subprocess.run(list(cmd), cwd=cwd or REPO, check=False)
    elapsed = time.monotonic() - start
    print(f"TIMING {label}={elapsed:.1f}s (exit {proc.returncode})")
    return proc.returncode


def _shell_install(*extras: str) -> list[str]:
    spec = f".[{','.join(extras)}]" if extras else "."
    if sys.platform == "win32":
        return [
            "powershell",
            "-NoProfile",
            "-Command",
            f"{sys.executable} -m pip install -U pip setuptools wheel; "
            f"{sys.executable} -m pip install -e '{spec}'",
        ]
    return [
        "bash",
        "-lc",
        f"{sys.executable} -m pip install -U pip setuptools wheel && "
        f"{sys.executable} -m pip install -e '{spec}'",
    ]


def _job_test() -> int:
    code = _run_step("install", _shell_install("test", "plot"))
    if code != 0:
        return code
    return _run_step(
        "pytest_tiers_1_3",
        [sys.executable, str(REPO / "scripts" / "run_tests.py"), "--", "--durations=15"],
    )


def _job_visa_sim() -> int:
    code = _run_step("install", _shell_install("test"))
    if code != 0:
        return code
    return _run_step(
        "visa_sim",
        [sys.executable, "-m", "pytest", "-m", "visa_sim", "-q"],
    )


def _job_docgen(*, skip_pdf: bool) -> int:
    env = os.environ.copy()
    env["COLOSSEUM_CI_TIMING"] = "1"
    code = _run_step("install", _shell_install("docs", "test"))
    if code != 0:
        return code

    steps: list[tuple[str, list[str]]] = [
        ("docgen_stage", [sys.executable, str(DOCGEN), "--stage-only"]),
        ("docgen_html", [sys.executable, str(DOCGEN), "--html-only"]),
    ]
    if not skip_pdf:
        if shutil.which("latexmk") is None:
            print("latexmk not found; skipping PDF phases (use --skip-pdf to silence)")
        else:
            steps.append(("docgen_pdf", [sys.executable, str(DOCGEN), "--pdf-only"]))

    for label, cmd in steps:
        print(f"\n== {label} ==")
        print("+", " ".join(cmd))
        start = time.monotonic()
        proc = subprocess.run(cmd, cwd=REPO, env=env, check=False)
        elapsed = time.monotonic() - start
        print(f"TIMING {label}={elapsed:.1f}s (exit {proc.returncode})")
        if proc.returncode != 0:
            return proc.returncode
    return 0


def _job_static() -> int:
    code = _run_step("install", _shell_install("static"))
    if code != 0:
        return code
    for tool in ("ruff", "mypy", "bandit", "vulture"):
        code = _run_step(
            f"static_{tool}",
            [sys.executable, str(REPO / "scripts" / "run_static.py"), "--tool", tool],
        )
        if code != 0:
            return code
    return 0


def _job_packaging() -> int:
    code = _run_step(
        "install_build",
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-U",
            "pip",
            "setuptools",
            "wheel",
            "build",
        ],
    )
    if code != 0:
        return code
    code = _run_step("build_sdist_wheel", [sys.executable, "-m", "build"])
    if code != 0:
        return code
    if sys.platform == "win32":
        smoke_cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"{sys.executable} -m venv $env:TEMP\\colosseum-packaging-venv; "
            f"$wheel = Get-ChildItem dist\\*.whl | Select-Object -First 1; "
            f"& $env:TEMP\\colosseum-packaging-venv\\Scripts\\pip install "
            f"\"$($wheel.FullName)[bench]\"; "
            f"& $env:TEMP\\colosseum-packaging-venv\\Scripts\\python -c "
            f"\"import pyvisa, paramiko, customtkinter\"; "
            f"& $env:TEMP\\colosseum-packaging-venv\\Scripts\\colosseum --help",
        ]
    else:
        smoke_cmd = [
            "bash",
            "-lc",
            "python -m venv /tmp/colosseum-packaging-venv && "
            "WHEEL=$(ls dist/*.whl) && "
            "/tmp/colosseum-packaging-venv/bin/pip install \"${WHEEL}[bench]\" && "
            "/tmp/colosseum-packaging-venv/bin/python -c "
            "\"import pyvisa, paramiko, customtkinter\" && "
            "/tmp/colosseum-packaging-venv/bin/colosseum --help",
        ]
    return _run_step("packaging_smoke", smoke_cmd)


def _job_offline() -> int:
    env = os.environ.copy()
    env["COLOSSEUM_CI_TIMING"] = "1"
    code = _run_step("install", _shell_install())
    if code != 0:
        return code
    print("\n== offline_bundle_regression ==")
    cmd = [sys.executable, str(REPO / "tests" / "regression" / "run_offline_install_check.py")]
    print("+", " ".join(cmd))
    start = time.monotonic()
    proc = subprocess.run(cmd, cwd=REPO, env=env, check=False)
    elapsed = time.monotonic() - start
    print(f"TIMING offline_bundle_regression={elapsed:.1f}s (exit {proc.returncode})")
    return proc.returncode


_JOBS: dict[str, Callable[[], int]] = {
    "test": _job_test,
    "visa-sim": _job_visa_sim,
    "docgen": lambda: _job_docgen(skip_pdf=False),
    "docgen-html": lambda: _job_docgen(skip_pdf=True),
    "static": _job_static,
    "packaging": _job_packaging,
    "offline": _job_offline,
}


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for local CI job timing mirrors.

    :param argv: Optional argument vector (defaults to ``sys.argv[1:]``).
    :type argv: list[str] | None, optional

    :returns: Process exit code (``0`` on success).
    :rtype: int
    """
    parser = argparse.ArgumentParser(description="Profile CI job commands locally")
    parser.add_argument(
        "--job",
        choices=sorted(_JOBS),
        required=True,
        help="CI job to mirror",
    )
    args = parser.parse_args(argv)
    total_start = time.monotonic()
    code = _JOBS[args.job]()
    total = time.monotonic() - total_start
    print(f"\nTIMING total={total:.1f}s")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
