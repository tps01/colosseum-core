"""Required verification without a prior measurement (must ERROR / exit 1)."""

from __future__ import annotations

from pathlib import Path

import colosseum as col

_CONFIG = Path(__file__).resolve().parents[3] / "examples" / "configs" / "bench.sim.toml"


def main() -> None:
    col.config.load_config(str(_CONFIG))
    col.equipment.dmm.verify_voltage(key="vrail_3v3", expected_val=3.3, tolerance=0.1)
