"""
Example: RF bench integration (dual PSU, E4407B, SSH, trace verify).

Copy examples/configs/bench.rf.hardware.toml.example to configs/bench.local.toml
and set resources/credentials for your lab.

Run:
  colosseum run examples/test_rf_bench_integration.py --config configs/bench.local.toml

Post-run plot (optional matplotlib):
  python examples/plot_trace.py outputs/<run>/traces/rf_hold.csv
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import colosseum as col

_CONFIG = Path(__file__).resolve().parent / "configs" / os.environ.get(
    "COLOSSEUM_BENCH_CONFIG", "bench.rf.hardware.toml.example"
)

# Adjust for your DUT/stimulus after calibration.
_VERIFY_FREQUENCY_HZ = 1.0e9
_EXPECTED_POWER_DBM = -42.5
_POWER_TOLERANCE_DBM = 3.0
_MAX_HOLD_DWELL_S = 5.0


def main() -> None:
    col.config.load_config(str(_CONFIG))

    col.equipment.psu.set_output(psu_id=1, enabled=True)
    col.equipment.psu.set_output(psu_id=2, enabled=True)

    col.equipment.speca.preset(speca_id=1)
    col.equipment.speca.set_center_frequency(speca_id=1, frequency=_VERIFY_FREQUENCY_HZ)
    col.equipment.speca.set_span(speca_id=1, span=500e6)
    col.equipment.speca.set_trace_mode(speca_id=1, trace=1, mode="MAXH")
    col.equipment.speca.set_continuous_sweep(speca_id=1, enabled=True)
    time.sleep(_MAX_HOLD_DWELL_S)

    col.shared.ssh.measure_stdout(ssh_id=1, command="echo bench-integration", key="sdr_cmd")

    col.equipment.speca.save_trace_data(speca_id=1, path="traces/rf_hold.csv")
    col.equipment.speca.measure_trace_power_at_frequency(
        speca_id=1,
        frequency_hz=_VERIFY_FREQUENCY_HZ,
        key="trace_power_1ghz",
    )
    col.equipment.speca.verify_trace_power_at_frequency(
        key="trace_power_1ghz",
        expected_val=_EXPECTED_POWER_DBM,
        tolerance=_POWER_TOLERANCE_DBM,
    )

    col.equipment.speca.set_marker_frequency(speca_id=1, marker=1, frequency_hz=_VERIFY_FREQUENCY_HZ)
    col.equipment.speca.measure_marker_power(speca_id=1, marker=1, key="marker_power_1ghz")
    col.equipment.speca.verify_marker_power(
        key="marker_power_1ghz",
        expected_val=_EXPECTED_POWER_DBM,
        tolerance=_POWER_TOLERANCE_DBM,
    )

    col.equipment.psu.set_output(psu_id=1, enabled=False)
    col.equipment.psu.set_output(psu_id=2, enabled=False)
    col.equipment.speca.set_trace_mode(speca_id=1, trace=1, mode="WRIT")


if __name__ == "__main__":
    main()
    col.endex()
