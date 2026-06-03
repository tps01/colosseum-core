#!/usr/bin/env python3
"""
Full Colosseum documentation build: modular autodoc + stitch + HTML + PDF.

1. Discover ``colosseum.docgen`` entry points (core + plugins + third-party)
2. Run :mod:`build_module` for each
3. Run :mod:`build_config_reference` and :mod:`stitch`
4. Run ``sphinx-build`` for HTML and LaTeX/PDF
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from _bootstrap import bootstrap

bootstrap()

from build_config_reference import build_config_reference_rst
from build_module import build_module
from build_pdf import build_pdf
from discover import discover_specs
from stitch import stitch


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_staged_site(
    *,
    docgen_root: Path | None = None,
    clean: bool = False,
) -> Path:
    """Stage autodoc RST, config reference, and stitched Sphinx source."""
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

    config_ref = docgen_root / "config_reference.rst"
    print("Building bench config reference")
    build_config_reference_rst(output_path=config_ref)

    return stitch(docgen_root=docgen_root, clean=clean)


def build_sphinx_html(*, site_source: Path, html_dir: Path, repo_root: Path) -> Path:
    html_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-b",
            "html",
            str(site_source),
            str(html_dir),
        ],
        cwd=repo_root,
        check=True,
    )
    return html_dir / "index.html"


def build_docs(
    *,
    docgen_root: Path | None = None,
    clean: bool = False,
    skip_html: bool = False,
    skip_pdf: bool = False,
) -> tuple[Path | None, Path | None]:
    repo_root = _repo_root()
    site_root = build_staged_site(docgen_root=docgen_root, clean=clean)
    site_source = site_root / "source"
    html_index: Path | None = None
    pdf_path: Path | None = None

    if not skip_html:
        html_dir = site_root / "html"
        print("Running sphinx-build (html)...")
        html_index = build_sphinx_html(
            site_source=site_source,
            html_dir=html_dir,
            repo_root=repo_root,
        )
        print(f"HTML output: {html_index}")

    if not skip_pdf:
        latex_dir = site_root / "latex"
        print("Running sphinx-build (latex) and latexmk...")
        pdf_path = build_pdf(
            site_source=site_source,
            latex_dir=latex_dir,
            repo_root=repo_root,
        )
        print(f"PDF output: {pdf_path}")

    return html_index, pdf_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build full Colosseum Sphinx documentation")
    parser.add_argument("--docgen-root", type=Path, help="Default: build/docgen")
    parser.add_argument("--clean", action="store_true", help="Remove staged outputs before build")
    parser.add_argument("--skip-html", action="store_true", help="Build PDF only (still runs staging)")
    parser.add_argument("--skip-pdf", action="store_true", help="Build HTML only (no LaTeX required)")
    args = parser.parse_args(argv)

    if args.skip_html and args.skip_pdf:
        parser.error("Cannot use both --skip-html and --skip-pdf")

    build_docs(
        docgen_root=args.docgen_root,
        clean=args.clean,
        skip_html=args.skip_html,
        skip_pdf=args.skip_pdf,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
