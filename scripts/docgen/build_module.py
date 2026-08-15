#!/usr/bin/env python3
"""
Generate autodoc RST for a single Colosseum module (core or plugin).

Usage:
  python scripts/docgen/build_module.py --spec colosseum
  python scripts/docgen/build_module.py --module-id colosseum

Writes ``build/docgen/<module_id>/rst/`` and ``manifest.json``.
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path

from _bootstrap import bootstrap

bootstrap()

from colosseum.docgen_spec import DocgenModuleSpec  # noqa: E402
from discover import discover_specs, write_manifest  # noqa: E402


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


def _write_module_index(
    rst_dir: Path, spec: DocgenModuleSpec, extra_stems: set[str]
) -> None:
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
    if (rst_dir / "modules.rst").is_file():
        lines.append("   modules")
    for stem in sorted(extra_stems - {"index", "modules"}):
        lines.append(f"   {stem}")
    lines.append("")
    (rst_dir / "index.rst").write_text("\n".join(lines), encoding="utf-8")


def _module_source_path(module: str) -> Path:
    spec = importlib.util.find_spec(module)
    if spec is None:
        raise SystemExit(f"Cannot locate module for docgen: {module}")
    if spec.submodule_search_locations:
        return Path(next(iter(spec.submodule_search_locations))).resolve()
    if spec.origin:
        return Path(spec.origin).resolve()
    raise SystemExit(f"Cannot locate source path for docgen module: {module}")


def _run_apidoc(rst_dir: Path, module: str) -> None:
    args = ["-f", "-e", "-M", "-o", str(rst_dir), str(_module_source_path(module))]
    try:
        from sphinx.ext.apidoc import main as apidoc_main

        if apidoc_main(args) != 0:
            raise RuntimeError(f"sphinx-apidoc failed for module {module}")
        return
    except ImportError as exc:
        raise SystemExit(
            'sphinx is required for docgen (pip install "colosseum-core[docs]")'
        ) from exc


def _patch_decorator_package_autodoc(rst_dir: Path) -> None:
    """Drop package-level re-exports that collide with submodule doc targets."""
    path = rst_dir / "colosseum.decorators.rst"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    marker = "   :exclude-members: command, measurement, verification\n"
    if marker in text:
        return
    for old_marker in (
        "   :exclude-members: measurement, verification\n",
        "   :exclude-members: command, measurement, verification\n",
    ):
        if old_marker in text:
            if old_marker != marker:
                path.write_text(text.replace(old_marker, marker, 1), encoding="utf-8")
            return
    needle = "   :undoc-members:\n"
    if needle not in text:
        return
    path.write_text(text.replace(needle, needle + marker, 1), encoding="utf-8")


def build_module(
    spec: DocgenModuleSpec,
    *,
    output_root: Path | None = None,
    clean: bool = False,
) -> Path:
    """Generate autodoc RST and manifest for one docgen module.

    :param spec: Module specification from an entry point.
    :type spec: DocgenModuleSpec
    :param output_root: Staging root (default: ``build/docgen``).
    :type output_root: Path | None, optional
    :param clean: When ``True``, remove the module staging directory first.
    :type clean: bool, optional

    :returns: Module staging directory containing ``rst/`` and ``manifest.json``.
    :rtype: Path
    """
    staging = _staging_dir(spec.module_id, output_root)
    rst_dir = staging / "rst"
    if clean and staging.exists():
        shutil.rmtree(staging)
    rst_dir.mkdir(parents=True, exist_ok=True)
    for old_rst in rst_dir.glob("*.rst"):
        old_rst.unlink()

    repo_root = _repo_root()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    for package in spec.import_packages:
        try:
            __import__(package)
        except ImportError as exc:
            raise SystemExit(f"Cannot import `{package}` for docgen: {exc}") from exc

    extra_stems: set[str] = set()
    for extra in spec.normalized_extra_rst_dirs():
        if extra.is_dir():
            for rst_file in extra.glob("*.rst"):
                shutil.copy2(rst_file, rst_dir / rst_file.name)
                extra_stems.add(rst_file.stem)

    for module in spec.autodoc_modules:
        _run_apidoc(rst_dir, module)

    _patch_decorator_package_autodoc(rst_dir)

    _write_module_index(rst_dir, spec, extra_stems)
    write_manifest(spec, staging, rst_subdir="rst")
    return staging


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for single-module autodoc generation.

    :param argv: Optional argument vector (defaults to ``sys.argv[1:]``).
    :type argv: list[str] | None, optional

    :returns: Process exit code (``0`` on success).
    :rtype: int
    """
    parser = argparse.ArgumentParser(description="Build autodoc RST for one Colosseum module")
    parser.add_argument("--module-id", help="Docgen module_id (for example colosseum)")
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
