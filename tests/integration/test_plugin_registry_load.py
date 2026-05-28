"""I-PLG-01: runtime plugins load via entry points (or monorepo fallback)."""

from __future__ import annotations

import colosseum as col
from colosseum.config import load_config
from colosseum.context import require_context
from colosseum.plugins.loader import ensure_plugins_loaded


def test_entry_points_register_equipment_and_shared(bench_sim, isolated_cwd) -> None:
    load_config(bench_sim)
    ctx = require_context()
    ensure_plugins_loaded(ctx.plugin_registry)
    specs = {s.dotted_path for s in ctx.plugin_registry.config_section_specs()}
    assert "equipment.psu" in specs
    assert "equipment.dmm" in specs
    assert "shared.ssh" in specs
    assert ctx.plugin_registry.has_namespace("equipment")
    assert ctx.plugin_registry.has_namespace("shared")
    assert hasattr(col.equipment, "psu")
    assert hasattr(col.shared, "ssh")
