#!/usr/bin/env python3
"""
Stitch modular docgen outputs and user guides into a single Sphinx source tree.

Reads ``build/docgen/*/manifest.json``, copies staged API RST, merges
``docs/sphinx/source/`` guides, and writes ``build/docgen/site/source/``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import textwrap
from pathlib import Path
from typing import List

from _bootstrap import bootstrap

bootstrap()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_manifests(docgen_root: Path) -> List[dict]:
    manifests: List[dict] = []
    if not docgen_root.is_dir():
        return manifests
    for child in sorted(docgen_root.iterdir()):
        manifest_path = child / "manifest.json"
        if manifest_path.is_file():
            manifests.append(json.loads(manifest_path.read_text(encoding="utf-8")))
    return sorted(manifests, key=lambda m: (m.get("order", 100), m.get("module_id", "")))


def _write_conf_py(target: Path, repo_root: Path) -> None:
    conf = textwrap.dedent(
        f'''
        import os
        import sys

        sys.path.insert(0, {str(repo_root)!r})

        project = "Colosseum"
        copyright = "Colosseum contributors"
        author = "Colosseum contributors"
        release = "0.3.0"

        extensions = [
            "sphinx.ext.autodoc",
            "sphinx.ext.napoleon",
            "sphinx.ext.viewcode",
            "sphinx.ext.intersphinx",
        ]

        templates_path = ["_templates"]
        exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

        html_theme = "alabaster"
        html_static_path = ["_static"]

        autodoc_member_order = "bysource"
        autodoc_typehints = "description"
        napoleon_google_docstring = True
        napoleon_numpy_docstring = True

        intersphinx_mapping = {{
            "python": ("https://docs.python.org/3", None),
        }}

        latex_engine = "pdflatex"
        '''
    ).strip() + "\n"
    (target / "conf.py").write_text(conf, encoding="utf-8")


def _write_api_index(site_source: Path, manifests: List[dict]) -> None:
    api_root = site_source / "api"
    api_root.mkdir(parents=True, exist_ok=True)
    lines = [
        "API Reference",
        "=============",
        "",
        ".. toctree::",
        "   :maxdepth: 2",
        "",
    ]
    for manifest in manifests:
        module_id = manifest["module_id"]
        title = manifest.get("title", module_id)
        lines.append(f"   {title} <{module_id}/index>")
    lines.append("")
    (api_root / "index.rst").write_text("\n".join(lines), encoding="utf-8")


def _write_site_index(site_source: Path, manifests: List[dict]) -> None:
    lines = [
        "Colosseum",
        "=========",
        "",
        "Bench test automation for embedded systems.",
        "",
        ".. toctree::",
        "   :maxdepth: 2",
        "   :caption: User guide",
        "",
        "   guides/installation",
        "   guides/offline_install",
        "   guides/quickstart",
        "   guides/configuration",
        "   guides/bench_config_reference",
        "   guides/io_digital",
        "   guides/rf_equipment",
        "   guides/running_tests",
        "   guides/running_suites",
        "   guides/output_artifacts",
        "   guides/exit_codes",
        "   guides/measurements_verifications",
        "   guides/plugins",
        "   guides/platform_notes",
        "",
        ".. toctree::",
        "   :maxdepth: 2",
        "   :caption: API reference",
        "",
        "   api/index",
        "",
    ]
    (site_source / "index.rst").write_text("\n".join(lines), encoding="utf-8")


def stitch(
    *,
    docgen_root: Path | None = None,
    guides_root: Path | None = None,
    site_root: Path | None = None,
    clean: bool = False,
) -> Path:
    repo_root = _repo_root()
    docgen_root = docgen_root or (repo_root / "build" / "docgen")
    guides_root = guides_root or (repo_root / "docs" / "sphinx" / "source")
    site_root = site_root or (docgen_root / "site")
    site_source = site_root / "source"

    if clean and site_root.exists():
        shutil.rmtree(site_root)
    site_source.mkdir(parents=True, exist_ok=True)
    (site_source / "_static").mkdir(exist_ok=True)
    (site_source / "_templates").mkdir(exist_ok=True)

    manifests = _load_manifests(docgen_root)
    if not manifests:
        raise SystemExit(f"No module manifests found under {docgen_root}")

    guides_dest = site_source / "guides"
    guides_src = guides_root / "guides" if (guides_root / "guides").is_dir() else guides_root
    if guides_src.is_dir():
        if guides_dest.exists():
            shutil.rmtree(guides_dest)
        shutil.copytree(guides_src, guides_dest)

    config_ref_src = docgen_root / "config_reference.rst"
    if config_ref_src.is_file():
        guides_dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config_ref_src, guides_dest / "bench_config_reference.rst")

    api_root = site_source / "api"
    api_root.mkdir(parents=True, exist_ok=True)
    for manifest in manifests:
        module_id = manifest["module_id"]
        src = docgen_root / module_id / manifest.get("rst_subdir", "rst")
        dest = api_root / module_id
        if dest.exists():
            shutil.rmtree(dest)
        if src.is_dir():
            shutil.copytree(src, dest)

    _write_conf_py(site_source, repo_root)
    _write_api_index(site_source, manifests)
    _write_site_index(site_source, manifests)
    return site_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stitch modular docgen RST into Sphinx site source")
    parser.add_argument("--docgen-root", type=Path, help="Default: build/docgen")
    parser.add_argument("--guides-root", type=Path, help="Default: docs/sphinx/source")
    parser.add_argument("--site-root", type=Path, help="Default: build/docgen/site")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args(argv)

    site_root = stitch(
        docgen_root=args.docgen_root,
        guides_root=args.guides_root,
        site_root=args.site_root,
        clean=args.clean,
    )
    print(f"Stitched site source: {site_root / 'source'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
