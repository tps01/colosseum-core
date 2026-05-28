#!/usr/bin/env python3
"""
Remove Colosseum build artifacts and temporary files from the repository tree.

Aligned with .gitignore (includes ``*.egg-info/``). Does not delete source, docs, or local secrets (.env).
By default, virtual environments are kept but safe generated artifacts inside them are removed.

Usage:
  python scripts/cleanup.py --dry-run
  python scripts/cleanup.py
  python scripts/cleanup.py --include-venvs
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import sys
from pathlib import Path
from typing import Iterable, List

# Top-level directories under repo root to remove entirely.
ROOT_DIRS = (
    "outputs",
    "build",
    "dist",
    "develop-eggs",
    "downloads",
    "eggs",
    ".eggs",
    "lib",
    "lib64",
    "parts",
    "sdist",
    "var",
    "wheels",
    "share",
    "pip-wheel-metadata",
    "htmlcov",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".hypothesis",
)

# Top-level dirs only removed with --include-venvs.
VENV_DIRS = (".venv", "venv", "ENV", "env")

# Directory names removed anywhere in the tree.
WALK_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".hypothesis"}

# Safe generated artifacts to remove inside virtual environments when the venv itself is kept.
VENV_ARTIFACT_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".hypothesis"}
VENV_ARTIFACT_FILE_GLOBS = ("*.py[cod]", "*$py.class")

# File globs removed anywhere in the tree.
WALK_FILE_GLOBS = (
    "*.py[cod]",
    "*$py.class",
    "*.so",
    ".coverage",
    ".DS_Store",
    "Thumbs.db",
    "Desktop.ini",
    "*.swp",
    "*.swo",
    "*~",
    "MANIFEST",
    "*.egg",
    "pip-log.txt",
)

# Directory globs anywhere in the tree (e.g. *.egg-info).
WALK_DIR_GLOBS = ("*.egg-info",)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _matches_any(name: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def _is_under_venv(root: Path, path: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    return bool(rel_parts and rel_parts[0] in VENV_DIRS)


def _collect_venv_artifacts(root: Path) -> List[Path]:
    targets: List[Path] = []
    for name in VENV_DIRS:
        venv = root / name
        if not venv.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(venv, topdown=True):
            current = Path(dirpath)
            for dirname in list(dirnames):
                if dirname in VENV_ARTIFACT_DIR_NAMES:
                    targets.append(current / dirname)
            dirnames[:] = [d for d in dirnames if d not in VENV_ARTIFACT_DIR_NAMES]
            for filename in filenames:
                if _matches_any(filename, VENV_ARTIFACT_FILE_GLOBS):
                    targets.append(current / filename)
    return targets


def _collect_paths(
    root: Path,
    *,
    include_venvs: bool,
) -> List[Path]:
    targets: List[Path] = []

    for name in ROOT_DIRS:
        path = root / name
        if path.exists():
            targets.append(path)

    if include_venvs:
        for name in VENV_DIRS:
            path = root / name
            if path.exists():
                targets.append(path)
    else:
        targets.extend(_collect_venv_artifacts(root))

    for egg_info in root.glob("*.egg-info"):
        if egg_info.is_dir():
            targets.append(egg_info)

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        current = Path(dirpath)

        if not include_venvs and _is_under_venv(root, current):
            dirnames.clear()
            continue

        for dirname in list(dirnames):
            if dirname in WALK_DIR_NAMES or _matches_any(dirname, WALK_DIR_GLOBS):
                targets.append(current / dirname)

        # Do not descend into paths we are removing (or venvs when skipped).
        skip_names = set(WALK_DIR_NAMES) | {d for d in dirnames if _matches_any(d, WALK_DIR_GLOBS)}
        if not include_venvs:
            skip_names |= set(VENV_DIRS)
        dirnames[:] = [d for d in dirnames if d not in skip_names]

        for filename in filenames:
            if _matches_any(filename, WALK_FILE_GLOBS):
                targets.append(current / filename)

    # Deduplicate: drop paths inside another target (keep outermost only).
    targets = sorted(set(targets), key=lambda p: (len(p.parts), str(p)))
    pruned: List[Path] = []
    for path in targets:
        if any(path != other and other in path.parents for other in targets):
            continue
        pruned.append(path)
    return sorted(pruned, key=lambda p: str(p))


def _format_size(path: Path) -> str:
    if path.is_file():
        return f"{path.stat().st_size} B"
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    if total < 1024:
        return f"{total} B"
    if total < 1024 * 1024:
        return f"{total / 1024:.1f} KiB"
    return f"{total / (1024 * 1024):.1f} MiB"


def _remove(path: Path, *, dry_run: bool) -> None:
    if dry_run:
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Remove build artifacts and temporary files")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List paths that would be removed without deleting anything",
    )
    parser.add_argument(
        "--include-venvs",
        action="store_true",
        help="Also remove .venv/, venv/, env/ at repository root",
    )
    args = parser.parse_args(argv)
    root = _repo_root()

    targets = _collect_paths(root, include_venvs=args.include_venvs)
    if not targets:
        print("Nothing to clean.")
        return 0

    mode = "DRY RUN" if args.dry_run else "REMOVE"
    print(f"{mode}: {len(targets)} path(s) under {root}\n")
    for path in targets:
        rel = path.relative_to(root)
        try:
            size = _format_size(path) if path.exists() else "missing"
        except OSError:
            size = "?"
        print(f"  {rel}  ({size})")

    if args.dry_run:
        print("\nNo files were deleted. Re-run without --dry-run to remove.")
        return 0

    for path in targets:
        _remove(path, dry_run=False)
    print("\nCleanup complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
