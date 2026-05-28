"""Required checks pass; optional verification fails — run must still exit 0."""

from __future__ import annotations

import os
from pathlib import Path

import colosseum as col

_REPO = Path(__file__).resolve().parents[3]
_CONFIG_NAME = os.environ.get("COLOSSEUM_BENCH_CONFIG", "bench.sim.toml")
_CONFIG = _REPO / "examples" / "configs" / _CONFIG_NAME


def main() -> None:
    col.config.load_config(str(_CONFIG))
    col.equipment.psu.set_voltage(psu_id=1, voltage=3.3)
    col.equipment.psu.set_output(psu_id=1, enabled=True)
    col.equipment.dmm.measure_voltage(dmm_id=1, channel=1, key="vrail_3v3")
    col.equipment.dmm.verify_voltage(key="vrail_3v3", expected_val=3.3, tolerance=0.1)
    col.equipment.dmm.measure_voltage(dmm_id=1, channel=2, key="probe_optional")
    col.equipment.dmm.verify_voltage(
        key="probe_optional", expected_val=1.8, tolerance=0.1, optional=True
    )


if __name__ == "__main__":
    main()
    col.endex()
