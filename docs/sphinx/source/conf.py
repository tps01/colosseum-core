"""Sphinx configuration for Colosseum core user documentation."""

from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


def _repo_root() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError(f"Could not locate pyproject.toml above {here}")


_pyproject = tomllib.loads((_repo_root() / "pyproject.toml").read_text(encoding="utf-8"))

project = "Colosseum"
copyright = "tps01"
author = "tps01"
release = str(_pyproject["project"]["version"])

extensions: list[str] = []

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"
html_static_path = ["_static"]
html_logo = "_static/colosseum-logo.png"
html_favicon = "_static/colosseum.ico"
html_theme_options = {
    "logo_name": True,
    "description": "Test automation for hardware and software",
}

latex_engine = "pdflatex"
latex_elements = {
    # Avoid blank verso pages before each short chapter in the PDF manual.
    "classoptions": ",openany",
}
latex_logo = "_static/colosseum-logo.png"
latex_documents = [
    ("index_pdf", "colosseum.tex", "Colosseum", "tps01", "manual"),
]
