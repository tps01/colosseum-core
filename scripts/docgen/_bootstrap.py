"""Ensure repository root and scripts/docgen are on sys.path for CLI scripts."""

from __future__ import annotations

import sys
from pathlib import Path


def bootstrap() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    docgen_dir = Path(__file__).resolve().parent
    for path in (repo_root, docgen_dir):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
    return repo_root
