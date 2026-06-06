"""I-PLG-01: runtime plugins load via entry points (or monorepo fallback)."""

from __future__ import annotations

import colosseum as col
from colosseum.config import load_config
from colosseum.context import require_context
from colosseum.plugins.loader import ensure_plugins_loaded


def test_entry_points_register_equipment_shared_and_io(bench_sim, isolated_cwd) -> None:
    load_config(bench_sim)
    ctx = require_context()
    ensure_plugins_loaded(ctx.plugin_registry)
    specs = {s.dotted_path for s in ctx.plugin_registry.config_section_specs()}
    assert "equipment.psu" in specs
    assert "equipment.dmm" in specs
    assert "equipment.attn" in specs
    assert "equipment.oscope" in specs
    assert "shared.ssh" in specs
    assert "io.dio" in specs
    assert ctx.plugin_registry.has_namespace("equipment")
    assert ctx.plugin_registry.has_namespace("shared")
    assert ctx.plugin_registry.has_namespace("io")
    assert ctx.plugin_registry.has_namespace("host")
    assert "host.profile" in specs
    assert hasattr(col.equipment, "psu")
    assert hasattr(col.equipment, "attn")
    assert hasattr(col.shared, "ssh")
    assert hasattr(col.io, "dio")
    assert hasattr(col.host, "system")
    assert hasattr(col.host, "bench")
    assert hasattr(col.host, "config")
