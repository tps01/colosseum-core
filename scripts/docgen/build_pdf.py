"""Build PDF documentation from a stitched Sphinx source tree."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

LATEX_INSTALL_HINT = """
LaTeX toolchain required for PDF output.

  Ubuntu/Debian: sudo apt-get install -y latexmk texlive-latex-recommended \\
      texlive-fonts-recommended texlive-latex-extra
  Windows: install MiKTeX or TeX Live and ensure latexmk is on PATH

Use --skip-pdf for HTML-only builds without LaTeX.
"""


def require_latex_toolchain() -> None:
    if shutil.which("latexmk") is None:
        raise SystemExit(LATEX_INSTALL_HINT.strip())


def _find_main_tex(latex_dir: Path) -> Path:
    candidates = sorted(latex_dir.glob("*.tex"))
    if not candidates:
        raise SystemExit(f"No .tex file found under {latex_dir}")
    preferred = latex_dir / "colosseum.tex"
    if preferred.is_file():
        return preferred
    if len(candidates) == 1:
        return candidates[0]
    raise SystemExit(f"Multiple .tex files in {latex_dir}; expected colosseum.tex")


def build_pdf(*, site_source: Path, latex_dir: Path, repo_root: Path) -> Path:
    """Run sphinx-build -b latex and latexmk; return path to the PDF."""
    require_latex_toolchain()
    latex_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-b",
            "latex",
            str(site_source),
            str(latex_dir),
        ],
        cwd=repo_root,
        check=True,
    )
    tex_path = _find_main_tex(latex_dir)
    subprocess.run(
        [
            "latexmk",
            "-pdf",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-cd",
            str(tex_path),
        ],
        cwd=repo_root,
        check=True,
    )
    pdf_path = tex_path.with_suffix(".pdf")
    if not pdf_path.is_file():
        raise SystemExit(f"Expected PDF at {pdf_path}")
    return pdf_path
