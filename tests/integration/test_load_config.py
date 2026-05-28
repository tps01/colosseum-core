"""I-CFG: load_config and plugin namespaces."""

from __future__ import annotations

import colosseum as col
from colosseum.config import load_config


def test_bench_sim_loads_equipment_and_shared_sections(bench_sim, isolated_cwd) -> None:
    store = load_config(bench_sim)
    psus = store.list_items("equipment.psu")
    assert len(psus) >= 2
    assert all(row.get("driver") == "sim" for row in psus)
    ssh_rows = store.list_items("shared.ssh")
    assert ssh_rows and ssh_rows[0].get("driver") == "sim"


def test_lazy_namespaces_resolve(bench_sim, isolated_cwd) -> None:
    load_config(bench_sim)
    assert hasattr(col.equipment, "psu")
    assert hasattr(col.shared, "ssh")
