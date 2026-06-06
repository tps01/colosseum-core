from __future__ import annotations

import importlib
import json
from pathlib import Path

from colosseum.docgen_spec import DOCGEN_ENTRY_GROUP, DocgenModuleSpec

# Monorepo fallback when entry-point metadata is not installed.
_BUILTIN_DOCGEN = (
    ("colosseum", "colosseum.docgen_entry", "spec"),
    ("equipment", "colosseum_equipment.docgen_entry", "spec"),
    ("shared", "colosseum_shared.docgen_entry", "spec"),
    ("host", "colosseum_host.docgen_entry", "spec"),
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_builtin_specs() -> list[DocgenModuleSpec]:
    specs: list[DocgenModuleSpec] = []
    for _name, module_name, attr in _BUILTIN_DOCGEN:
        module = importlib.import_module(module_name)
        specs.append(getattr(module, attr)())
    return specs


def discover_specs() -> list[DocgenModuleSpec]:
    """Load all ``colosseum.docgen`` entry points; fall back to built-ins in source tree.

    :returns: Sorted list of docgen module specifications.
    :rtype: list[DocgenModuleSpec]
    """
    from colosseum.compat.entry_points import entry_points_for_group

    eps = entry_points_for_group(DOCGEN_ENTRY_GROUP)
    if not eps:
        return sorted(_load_builtin_specs(), key=lambda s: s.order)

    specs: list[DocgenModuleSpec] = []
    for ep in eps:
        factory = ep.load()
        item = factory() if callable(factory) else factory
        if not isinstance(item, DocgenModuleSpec):
            raise TypeError(f"Entry point `{ep.name}` must return DocgenModuleSpec")
        specs.append(item)
    return sorted(specs, key=lambda s: (s.order, s.module_id))


def write_manifest(spec: DocgenModuleSpec, staging_dir: Path, rst_subdir: str) -> Path:
    """Write ``manifest.json`` for a staged docgen module.

    :param spec: Module specification from an entry point.
    :type spec: DocgenModuleSpec
    :param staging_dir: Staging directory for this module (e.g. ``build/docgen/colosseum``).
    :type staging_dir: Path
    :param rst_subdir: Relative subdirectory containing generated RST (usually ``rst``).
    :type rst_subdir: str

    :returns: Path to the written manifest file.
    :rtype: Path
    """
    manifest = {
        "module_id": spec.module_id,
        "title": spec.title,
        "namespace": spec.namespace,
        "order": spec.order,
        "rst_subdir": rst_subdir,
        "index_doc": "index",
    }
    path = staging_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path
