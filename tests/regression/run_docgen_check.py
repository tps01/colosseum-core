#!/usr/bin/env python3
"""R-DOC-01: verify Sphinx docgen build succeeds."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "scripts" / "docgen" / "build_all.py"


def main() -> int:
    if not BUILD.is_file():
        print(f"Missing docgen script: {BUILD}", file=sys.stderr)
        return 2
    proc = subprocess.run([sys.executable, str(BUILD)], cwd=REPO, timeout=600)
    if proc.returncode != 0:
        print("DOCGEN FAIL: build_all.py returned non-zero", file=sys.stderr)
        return proc.returncode
    html = REPO / "build" / "docgen" / "site" / "html" / "index.html"
    if not html.is_file():
        print(f"DOCGEN FAIL: expected HTML at {html}", file=sys.stderr)
        return 1
    print(f"DOCGEN PASS: {html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
