from __future__ import annotations

import json
import re
from pathlib import Path

from .paths import sanitize_logical_name


def list_run_directories(cwd: Path) -> list[Path]:
    outputs_root = cwd / "outputs"
    if not outputs_root.is_dir():
        return []
    runs = [p for p in outputs_root.iterdir() if p.is_dir()]
    runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return runs


def _matches_logical_name(dir_name: str, logical_name: str) -> bool:
    sanitized = sanitize_logical_name(logical_name)
    if dir_name.endswith(f"_{sanitized}"):
        return True
    pattern = rf"^.*_{re.escape(sanitized)}_\d+$"
    return bool(re.match(pattern, dir_name))


def find_run_directory(
    cwd: Path,
    logical_name: str,
    since: float | None = None,
) -> Path | None:
    outputs_root = cwd / "outputs"
    if not outputs_root.is_dir():
        return None

    candidates: list[Path] = []
    for run_dir in outputs_root.iterdir():
        if not run_dir.is_dir():
            continue
        if since is not None and run_dir.stat().st_mtime < since:
            continue
        if _matches_logical_name(run_dir.name, logical_name):
            candidates.append(run_dir)

    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def read_summary_json(run_dir: Path) -> dict | None:
    summary_path = run_dir / "summary.json"
    if not summary_path.is_file():
        return None
    return json.loads(summary_path.read_text(encoding="utf-8"))
