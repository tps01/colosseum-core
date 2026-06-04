#!/usr/bin/env python3
"""R-OFFLINE-00: build end-user runtime bundle and install without network access."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKAGE_SCRIPT = REPO / "scripts" / "package_offline.py"
STAGING = REPO / "offline-bundle"
SMOKE_SCRIPT = STAGING / "smoke" / "run_sim.py"
SMOKE_CONFIG = STAGING / "smoke" / "bench.sim.toml"
WHEELS = STAGING / "wheels"


def _venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _run_bundle_install() -> Path:
    venv_dir = STAGING / ".venv"
    if venv_dir.exists():
        shutil.rmtree(venv_dir)

    if sys.platform == "win32":
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(STAGING / "install.ps1"),
            ],
            check=True,
            cwd=STAGING,
        )
    else:
        subprocess.run(["sh", str(STAGING / "install.sh")], check=True, cwd=STAGING)

    venv_python = _venv_python(venv_dir)
    if not venv_python.is_file():
        raise RuntimeError(f"install script did not create venv at {venv_dir}")
    return venv_python


def main() -> int:
    if not PACKAGE_SCRIPT.is_file():
        print(f"Missing packaging script: {PACKAGE_SCRIPT}", file=sys.stderr)
        return 2

    proc = subprocess.run([sys.executable, str(PACKAGE_SCRIPT)], cwd=REPO, timeout=900)
    if proc.returncode != 0:
        print("OFFLINE FAIL: package_offline.py returned non-zero", file=sys.stderr)
        return proc.returncode

    for path in (WHEELS, SMOKE_SCRIPT, STAGING / "install.sh", STAGING / "install.ps1"):
        if not path.exists():
            print(f"OFFLINE FAIL: offline-bundle staging incomplete ({path})", file=sys.stderr)
            return 1

    try:
        venv_python = _run_bundle_install()

        help_proc = subprocess.run([str(venv_python), "-m", "colosseum.runner.cli", "--help"], cwd=STAGING)
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
            cwd=STAGING,
        )
        if smoke_proc.returncode != 0:
            print("OFFLINE FAIL: smoke test returned non-zero", file=sys.stderr)
            return smoke_proc.returncode
    finally:
        shutil.rmtree(STAGING / ".venv", ignore_errors=True)

    print("OFFLINE PASS: bundle install and smoke test succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
