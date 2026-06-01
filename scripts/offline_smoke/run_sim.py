"""Minimal sim smoke test for offline install bundles."""

from __future__ import annotations

from pathlib import Path

import colosseum as col

_CONFIG = Path(__file__).resolve().parent / "bench.sim.toml"


def main() -> None:
    col.config.load_config(str(_CONFIG))
    col.equipment.dmm.measure_voltage(dmm_id=1, channel=1, key="offline_smoke")
    col.equipment.dmm.verify_voltage(key="offline_smoke", expected_val=3.3, tolerance=0.5)
