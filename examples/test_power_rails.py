"""
Target example: bench power-rail acceptance test (Wave 2+).

Development goal:
  - col.config.load_config initializes runtime
  - PSU/DMM high-level APIs persist measurements and verifications
  - Optional verification does not gate exit code
  - Raw SCPI escape hatch available alongside decorated APIs

Run when implemented:
  python examples/test_power_rails.py
  colosseum run examples/test_power_rails.py --config examples/configs/bench.toml

Expected artifacts (under outputs/<timestamp>_test_power_rails/):
  debug.log, execution.sqlite
"""

from __future__ import annotations
import os
from pathlib import Path
import colosseum as col

_CONFIG = Path(__file__).resolve().parent / "configs" / os.environ.get("COLOSSEUM_BENCH_CONFIG", "bench.toml")


def main() -> None:
    col.config.load_config(str(_CONFIG))

    # --- Stimulus: configure supply and enable output ---
    col.equipment.psu.set_voltage(psu_id=1, voltage=3.3)
    col.equipment.psu.set_current_limit(psu_id=1, current=1.0)
    col.equipment.psu.set_output(psu_id=1, enabled=True)

    # --- Measurement + required verification (architecture doc flow) ---
    col.equipment.dmm.measure_voltage(dmm_id=1, channel=1, key="vrail_3v3")
    col.equipment.dmm.verify_voltage(key="vrail_3v3", expected_val=3.3, tolerance=0.1)

    col.equipment.dmm.measure_voltage(dmm_id=1, channel=2, key="engineering_probe_point")
    # --- Optional engineering check (FAIL/ERROR must not fail the run) ---
    col.equipment.dmm.verify_voltage(key="engineering_probe_point", expected_val=1.8, tolerance=0.1, optional=True)

    # --- Escape hatch: direct SCPI readback for bring-up / debug ---
    readback = col.equipment.scpi.query_float(psu_id=1, command="VOLT?")
    # Implementations may log at DEBUG; high-level APIs remain preferred in tests.

    if readback < 3.0:
        # Illustrative host-side guard; real tests should prefer verify_* APIs.
        raise RuntimeError(f"PSU readback unexpectedly low: {readback}")


if __name__ == "__main__":
    main()
    col.endex()
