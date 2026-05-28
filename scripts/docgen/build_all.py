#!/usr/bin/env python3
"""
Full Colosseum documentation build: modular autodoc + stitch + HTML.

1. Discover ``colosseum.docgen`` entry points (core + plugins + third-party)
2. Run :mod:`build_module` for each
3. Run :mod:`stitch` to merge API RST and user guides
4. Run ``sphinx-build`` on the stitched site
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from _bootstrap import bootstrap

bootstrap()

from build_module import build_module
from discover import discover_specs
from stitch import stitch


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_html(
    *,
    docgen_root: Path | None = None,
    clean: bool = False,
    skip_html: bool = False,
) -> Path:
    repo_root = _repo_root()
    docgen_root = docgen_root or (repo_root / "build" / "docgen")
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    specs = discover_specs()
    if not specs:
        raise SystemExit("No docgen module specs discovered")

    for spec in specs:
        print(f"Building module docs: {spec.module_id} ({spec.title})")
        build_module(spec, output_root=docgen_root, clean=clean)

    site_root = stitch(docgen_root=docgen_root, clean=clean)
    site_source = site_root / "source"
    html_dir = site_root / "html"

    if skip_html:
        return html_dir

    html_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "sphinx",
        "-b",
        "html",
        str(site_source),
        str(html_dir),
    ]
    print("Running sphinx-build...")
    subprocess.run(cmd, cwd=repo_root, check=True)
    print(f"HTML output: {html_dir / 'index.html'}")
    return html_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build full Colosseum Sphinx documentation")
    parser.add_argument("--docgen-root", type=Path, help="Default: build/docgen")
    parser.add_argument("--clean", action="store_true", help="Remove staged outputs before build")
    parser.add_argument("--skip-html", action="store_true", help="Only generate RST source tree")
    args = parser.parse_args(argv)

    build_html(docgen_root=args.docgen_root, clean=args.clean, skip_html=args.skip_html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
