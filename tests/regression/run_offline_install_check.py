#!/usr/bin/env python3
"""R-OFFLINE-00: build end-user runtime bundle and install without network access."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKAGE_SCRIPT = REPO / "scripts" / "package_offline.py"
SMOKE_SCRIPT = REPO / "offline-bundle" / "smoke" / "run_sim.py"
SMOKE_CONFIG = REPO / "offline-bundle" / "smoke" / "bench.sim.toml"
WHEELS = REPO / "offline-bundle" / "wheels"


def _read_version() -> str:
    import re

    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise RuntimeError("Could not read version from pyproject.toml")
    return match.group(1)


def main() -> int:
    if not PACKAGE_SCRIPT.is_file():
        print(f"Missing packaging script: {PACKAGE_SCRIPT}", file=sys.stderr)
        return 2

    proc = subprocess.run([sys.executable, str(PACKAGE_SCRIPT)], cwd=REPO, timeout=900)
    if proc.returncode != 0:
        print("OFFLINE FAIL: package_offline.py returned non-zero", file=sys.stderr)
        return proc.returncode

    if not WHEELS.is_dir() or not SMOKE_SCRIPT.is_file():
        print("OFFLINE FAIL: offline-bundle staging incomplete", file=sys.stderr)
        return 1

    version = _read_version()
    venv_dir = Path(tempfile.mkdtemp(prefix="colosseum-offline-"))
    try:
        venv_python = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True, cwd=REPO)
        subprocess.run(
            [
                str(venv_python),
                "-m",
                "pip",
                "install",
                "--no-index",
                f"--find-links={WHEELS}",
                f"colosseum=={version}",
            ],
            check=True,
            cwd=REPO,
        )
        help_proc = subprocess.run([str(venv_python), "-m", "colosseum.runner.cli", "--help"], cwd=REPO)
        if help_proc.returncode != 0:
            print("OFFLINE FAIL: colosseum --help failed", file=sys.stderr)
            return help_proc.returncode

        smoke_proc = subprocess.run(
            [
                str(venv_python),
                "-m",
                "colosseum.runner.cli",
                "run",
                str(SMOKE_SCRIPT),
                "--config",
                str(SMOKE_CONFIG),
            ],
            cwd=REPO,
        )
        if smoke_proc.returncode != 0:
            print("OFFLINE FAIL: smoke test returned non-zero", file=sys.stderr)
            return smoke_proc.returncode
    finally:
        shutil.rmtree(venv_dir, ignore_errors=True)

    print("OFFLINE PASS: bundle install and smoke test succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
