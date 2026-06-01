"""
Example: RF sweep with VSG stimulus and spectrum analyzer trace capture.

Run:
  colosseum run examples/test_rf_sweep.py --config examples/configs/bench.rf.visa-sim.toml
"""

from __future__ import annotations

import os
from pathlib import Path

import colosseum as col

_CONFIG = Path(__file__).resolve().parent / "configs" / os.environ.get(
    "COLOSSEUM_BENCH_CONFIG", "bench.rf.visa-sim.toml"
)


def main() -> None:
    col.config.load_config(str(_CONFIG))

    col.equipment.vsg.set_frequency(vsg_id=1, frequency=1e9)
    col.equipment.vsg.set_power(vsg_id=1, power_dbm=-10.0)
    col.equipment.vsg.set_output(vsg_id=1, enabled=True)

    col.equipment.speca.set_center_frequency(speca_id=1, frequency=1e9)
    col.equipment.speca.set_span(speca_id=1, span=10e6)
    col.equipment.speca.set_rbw(speca_id=1, rbw=100e3)
    col.equipment.speca.peak_search(speca_id=1, marker=1)
    col.equipment.speca.measure_marker_power(speca_id=1, marker=1, key="carrier_power")
    col.equipment.speca.save_trace_data(speca_id=1, path="traces/carrier.csv")


if __name__ == "__main__":
    main()
    col.endex()
