"""Shared helpers for static analysis runners."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE_PACKAGES: tuple[str, ...] = ("colosseum",)
SCRIPTS_DIR = REPO / "scripts"
SCAN_PATHS: tuple[str, ...] = (*SOURCE_PACKAGES, "scripts")


def run_tool(cmd: list[str], *, cwd: Path = REPO, timeout: int = 600) -> int:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        timeout=timeout,
        check=False,
    )
    return int(proc.returncode)


def tool_executable(name: str) -> str:
    return str(Path(sys.executable).parent / name)
