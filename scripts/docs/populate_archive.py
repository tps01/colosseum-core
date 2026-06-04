#!/usr/bin/env python3
"""Copy archived documentation paths from git tag into gitignored docs/archive/."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_TAG = "doc-snapshot-pre-archive"
REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "docs" / "archive" / "MANIFEST.md"
ARCHIVE_ROOT = REPO_ROOT / "docs" / "archive"


def _parse_manifest(manifest_path: Path) -> list[str]:
    text = manifest_path.read_text(encoding="utf-8")
    paths: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^\|\s*`([^`]+)`\s*\|", line)
        if match:
            paths.append(match.group(1))
    return paths


def _git_show(tag: str, path: str) -> bytes | None:
    proc = subprocess.run(
        ["git", "show", f"{tag}:{path}"],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def populate(*, tag: str, paths: list[str]) -> int:
    errors = 0
    for rel_path in paths:
        payload = _git_show(tag, rel_path)
        if payload is None:
            print(f"SKIP (missing at {tag}): {rel_path}", file=sys.stderr)
            errors += 1
            continue
        dest = ARCHIVE_ROOT / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)
        print(f"Wrote {dest.relative_to(REPO_ROOT)}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Populate docs/archive from a git tag")
    parser.add_argument("--tag", default=DEFAULT_TAG, help=f"Default: {DEFAULT_TAG}")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args(argv)

    if not args.manifest.is_file():
        print(f"Missing manifest: {args.manifest}", file=sys.stderr)
        return 2

    paths = _parse_manifest(args.manifest)
    if not paths:
        print("No paths found in manifest table", file=sys.stderr)
        return 2

    errors = populate(tag=args.tag, paths=paths)
    if errors:
        print(
            f"\n{errors} path(s) failed. Create tag first, e.g.\n"
            f"  git tag -a {args.tag} -m \"Pre-archive doc snapshot\"\n",
            file=sys.stderr,
        )
        return 1
    print(f"\nDone. Tag-recovered files are under {ARCHIVE_ROOT} (gitignored except README, MANIFEST, and planning/).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
