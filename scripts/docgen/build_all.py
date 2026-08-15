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
import shutil
import subprocess
import sys
from pathlib import Path

from _bootstrap import bootstrap

bootstrap()

_scripts_dir = Path(__file__).resolve().parents[1]
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from build_config_reference import build_config_reference_rst  # noqa: E402
from build_module import build_module  # noqa: E402
from build_pdf import build_pdf  # noqa: E402
from discover import discover_specs  # noqa: E402
from stitch import stitch  # noqa: E402

from ci.timing import ci_phase  # noqa: E402


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_docgen_root(docgen_root: Path | None) -> Path:
    return docgen_root or (_repo_root() / "build" / "docgen")


def _site_root(docgen_root: Path | None) -> Path:
    return _default_docgen_root(docgen_root) / "site"


def _require_staged_site(docgen_root: Path | None) -> tuple[Path, Path]:
    site_root = _site_root(docgen_root)
    site_source = site_root / "source"
    if not site_source.is_dir():
        raise SystemExit(
            f"Staged Sphinx source not found at {site_source}; run --stage-only first"
        )
    return site_root, site_source


def build_staged_site(
    *,
    docgen_root: Path | None = None,
    clean: bool = False,
) -> Path:
    """Stage autodoc RST, config reference, and stitched Sphinx source.

    :param docgen_root: Staging root (default: ``build/docgen`` under repo root).
    :type docgen_root: Path | None, optional
    :param clean: When ``True``, remove staged module outputs before rebuilding.
    :type clean: bool, optional

    :returns: Site root directory (contains ``source/`` for ``sphinx-build``).
    :rtype: Path
    """
    repo_root = _repo_root()
    docgen_root = _default_docgen_root(docgen_root)
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    with ci_phase("staging"):
        specs = discover_specs()
        if not specs:
            raise SystemExit("No docgen module specs discovered")

        active_module_ids = {spec.module_id for spec in specs}
        staged_children = docgen_root.iterdir() if docgen_root.is_dir() else ()
        for child in staged_children:
            if (
                child.is_dir()
                and (child / "manifest.json").is_file()
                and child.name not in active_module_ids
            ):
                shutil.rmtree(child)

        for spec in specs:
            print(f"Building module docs: {spec.module_id} ({spec.title})")
            build_module(spec, output_root=docgen_root, clean=clean)

        config_ref = docgen_root / "config_reference.rst"
        print("Building bench config reference")
        build_config_reference_rst(output_path=config_ref)

        return stitch(docgen_root=docgen_root, clean=clean)


def build_sphinx_html(*, site_source: Path, html_dir: Path, repo_root: Path) -> Path:
    """Run ``sphinx-build -b html`` and return the index path.

    :param site_source: Stitched Sphinx source tree.
    :type site_source: Path
    :param html_dir: HTML output directory.
    :type html_dir: Path
    :param repo_root: Repository root (sphinx working directory).
    :type repo_root: Path

    :returns: Path to ``index.html``.
    :rtype: Path
    """
    html_dir.mkdir(parents=True, exist_ok=True)
    with ci_phase("html"):
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
    """Stage documentation and build HTML and/or PDF outputs.

    :param docgen_root: Staging root (default: ``build/docgen``).
    :type docgen_root: Path | None, optional
    :param clean: When ``True``, remove staged outputs before rebuilding.
    :type clean: bool, optional
    :param skip_html: When ``True``, skip the HTML ``sphinx-build`` step.
    :type skip_html: bool, optional
    :param skip_pdf: When ``True``, skip LaTeX/PDF generation.
    :type skip_pdf: bool, optional

    :returns: ``(html_index, pdf_path)``; either element may be ``None`` when skipped.
    :rtype: tuple[Path | None, Path | None]
    """
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
        with ci_phase("pdf"):
            pdf_path = build_pdf(
                site_source=site_source,
                latex_dir=latex_dir,
                repo_root=repo_root,
            )
        print(f"PDF output: {pdf_path}")

    return html_index, pdf_path


def build_html_only(*, docgen_root: Path | None = None) -> Path:
    """Build HTML from an already-staged Sphinx source tree.

    :param docgen_root: Staging root (default: ``build/docgen``).
    :type docgen_root: Path | None, optional

    :returns: Path to ``index.html``.
    :rtype: Path
    """
    site_root, site_source = _require_staged_site(docgen_root)
    html_dir = site_root / "html"
    print("Running sphinx-build (html)...")
    html_index = build_sphinx_html(
        site_source=site_source,
        html_dir=html_dir,
        repo_root=_repo_root(),
    )
    print(f"HTML output: {html_index}")
    return html_index


def build_pdf_only(*, docgen_root: Path | None = None) -> Path:
    """Build PDF from an already-staged Sphinx source tree.

    :param docgen_root: Staging root (default: ``build/docgen``).
    :type docgen_root: Path | None, optional

    :returns: Path to the generated PDF file.
    :rtype: Path
    """
    site_root, site_source = _require_staged_site(docgen_root)
    latex_dir = site_root / "latex"
    print("Running sphinx-build (latex) and latexmk...")
    with ci_phase("pdf"):
        pdf_path = build_pdf(
            site_source=site_source,
            latex_dir=latex_dir,
            repo_root=_repo_root(),
        )
    print(f"PDF output: {pdf_path}")
    return pdf_path


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the full documentation build pipeline.

    :param argv: Optional argument vector (defaults to ``sys.argv[1:]``).
    :type argv: list[str] | None, optional

    :returns: Process exit code (``0`` on success).
    :rtype: int
    """
    parser = argparse.ArgumentParser(description="Build full Colosseum Sphinx documentation")
    parser.add_argument("--docgen-root", type=Path, help="Default: build/docgen")
    parser.add_argument("--clean", action="store_true", help="Remove staged outputs before build")
    parser.add_argument(
        "--skip-html", action="store_true", help="Build PDF only (still runs staging)"
    )
    parser.add_argument(
        "--skip-pdf", action="store_true", help="Build HTML only (no LaTeX required)"
    )
    parser.add_argument(
        "--stage-only",
        action="store_true",
        help="Run autodoc staging and stitch only (no sphinx-build)",
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Build HTML only; requires prior --stage-only output",
    )
    parser.add_argument(
        "--pdf-only",
        action="store_true",
        help="Build PDF only; requires prior --stage-only output",
    )
    args = parser.parse_args(argv)

    phase_flags = sum(
        1 for flag in (args.stage_only, args.html_only, args.pdf_only) if flag
    )
    if phase_flags and (args.skip_html or args.skip_pdf):
        parser.error("Phase flags cannot be combined with --skip-html or --skip-pdf")
    if phase_flags > 1:
        parser.error("Use only one of --stage-only, --html-only, or --pdf-only")
    if args.skip_html and args.skip_pdf:
        parser.error("Cannot use both --skip-html and --skip-pdf")

    if args.stage_only:
        build_staged_site(docgen_root=args.docgen_root, clean=args.clean)
        return 0
    if args.html_only:
        build_html_only(docgen_root=args.docgen_root)
        return 0
    if args.pdf_only:
        build_pdf_only(docgen_root=args.docgen_root)
        return 0

    build_docs(
        docgen_root=args.docgen_root,
        clean=args.clean,
        skip_html=args.skip_html,
        skip_pdf=args.skip_pdf,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
