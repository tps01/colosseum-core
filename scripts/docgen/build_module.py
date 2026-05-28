#!/usr/bin/env python3
"""
Generate autodoc RST for a single Colosseum module (core or plugin).

Usage:
  python scripts/docgen/build_module.py --spec colosseum
  python scripts/docgen/build_module.py --module-id colosseum_equipment

Writes ``build/docgen/<module_id>/rst/`` and ``manifest.json``.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from _bootstrap import bootstrap

bootstrap()

from colosseum.docgen_spec import DocgenModuleSpec
from discover import discover_specs, write_manifest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _staging_dir(module_id: str, output_root: Path | None) -> Path:
    root = output_root or (_repo_root() / "build" / "docgen")
    return root / module_id


def _resolve_spec(module_id: str | None, spec_name: str | None) -> DocgenModuleSpec:
    specs = discover_specs()
    if module_id:
        for item in specs:
            if item.module_id == module_id:
                return item
        raise SystemExit(f"Unknown module_id: {module_id}")
    if spec_name:
        for item in specs:
            if item.module_id == spec_name or item.module_id.startswith(spec_name):
                return item
        raise SystemExit(f"Unknown spec name: {spec_name}")
    raise SystemExit("Provide --module-id or --spec")


def _write_module_index(rst_dir: Path, spec: DocgenModuleSpec) -> None:
    lines = [
        spec.title,
        "=" * len(spec.title),
        "",
    ]
    if spec.namespace:
        lines.append(f"User namespace: ``col.{spec.namespace}``")
        lines.append("")
    lines.append(".. toctree::")
    lines.append("   :maxdepth: 2")
    lines.append("")
    for path in sorted(rst_dir.glob("*.rst")):
        if path.stem == "index":
            continue
        lines.append(f"   {path.stem}")
    lines.append("")
    (rst_dir / "index.rst").write_text("\n".join(lines), encoding="utf-8")


def _run_apidoc(rst_dir: Path, repo_root: Path, module: str) -> None:
    args = ["-f", "-e", "-M", "-o", str(rst_dir), str(repo_root), module]
    try:
        from sphinx.ext.apidoc import main as apidoc_main

        if apidoc_main(args) != 0:
            raise RuntimeError(f"sphinx-apidoc failed for module {module}")
        return
    except ImportError as exc:
        raise SystemExit("sphinx is required for docgen (pip install colosseum[docs])") from exc


def build_module(
    spec: DocgenModuleSpec,
    *,
    output_root: Path | None = None,
    clean: bool = False,
) -> Path:
    staging = _staging_dir(spec.module_id, output_root)
    rst_dir = staging / "rst"
    if clean and staging.exists():
        shutil.rmtree(staging)
    rst_dir.mkdir(parents=True, exist_ok=True)

    repo_root = _repo_root()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    for package in spec.import_packages:
        try:
            __import__(package)
        except ImportError as exc:
            raise SystemExit(f"Cannot import `{package}` for docgen: {exc}") from exc

    for extra in spec.normalized_extra_rst_dirs():
        if extra.is_dir():
            for rst_file in extra.glob("*.rst"):
                shutil.copy2(rst_file, rst_dir / rst_file.name)

    for module in spec.autodoc_modules:
        _run_apidoc(rst_dir, repo_root, module)

    _write_module_index(rst_dir, spec)
    write_manifest(spec, staging, rst_subdir="rst")
    return staging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build autodoc RST for one Colosseum module")
    parser.add_argument("--module-id", help="Docgen module_id (e.g. colosseum_equipment)")
    parser.add_argument("--spec", help="Alias for module_id (e.g. equipment)")
    parser.add_argument("--output-root", type=Path, help="Default: build/docgen")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args(argv)

    spec = _resolve_spec(args.module_id, args.spec or args.module_id)
    staging = build_module(spec, output_root=args.output_root, clean=args.clean)
    print(f"Wrote {staging / 'rst'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
