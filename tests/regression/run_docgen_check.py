#!/usr/bin/env python3
"""R-DOC-01: verify Sphinx docgen build succeeds."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "scripts" / "docgen" / "build_all.py"


def main() -> int:
    if not BUILD.is_file():
        print(f"Missing docgen script: {BUILD}", file=sys.stderr)
        return 2

    skip_pdf = shutil.which("latexmk") is None
    if skip_pdf:
        print("DOCGEN: latexmk not found; running HTML-only (--skip-pdf)")
        cmd = [sys.executable, str(BUILD), "--skip-pdf"]
    else:
        cmd = [sys.executable, str(BUILD)]

    proc = subprocess.run(cmd, cwd=REPO, timeout=900)
    if proc.returncode != 0:
        print("DOCGEN FAIL: build_all.py returned non-zero", file=sys.stderr)
        return proc.returncode

    config_ref = REPO / "build" / "docgen" / "config_reference.rst"
    if not config_ref.is_file():
        print(f"DOCGEN FAIL: expected {config_ref}", file=sys.stderr)
        return 1
    ref_text = config_ref.read_text(encoding="utf-8")
    if "``psu_id``" not in ref_text or "``resource``" not in ref_text:
        print("DOCGEN FAIL: config_reference.rst missing psu_id / resource", file=sys.stderr)
        return 1

    html = REPO / "build" / "docgen" / "site" / "html" / "index.html"
    if not html.is_file():
        print(f"DOCGEN FAIL: expected HTML at {html}", file=sys.stderr)
        return 1

    index_pdf = REPO / "build" / "docgen" / "site" / "source" / "index_pdf.rst"
    if not index_pdf.is_file():
        print(f"DOCGEN FAIL: expected PDF master doc at {index_pdf}", file=sys.stderr)
        return 1
    pdf_index_text = index_pdf.read_text(encoding="utf-8")
    if "guides/plugins" in pdf_index_text:
        print("DOCGEN FAIL: index_pdf.rst must not include developer plugin guide", file=sys.stderr)
        return 1
    user_api_index = REPO / "build" / "docgen" / "site" / "source" / "user_api" / "index.rst"
    if not user_api_index.is_file():
        print(f"DOCGEN FAIL: expected user API RST at {user_api_index}", file=sys.stderr)
        return 1

    if not skip_pdf:
        pdf_files = list((REPO / "build" / "docgen" / "site" / "latex").glob("*.pdf"))
        if not pdf_files:
            print("DOCGEN FAIL: expected PDF under build/docgen/site/latex/", file=sys.stderr)
            return 1
        print(f"DOCGEN PASS: {html} and {pdf_files[0]}")
    else:
        print(f"DOCGEN PASS: {html} (PDF skipped; install latexmk for full build)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
