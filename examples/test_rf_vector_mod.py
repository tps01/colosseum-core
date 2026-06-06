"""
Example: vector waveform upload and RTSA capture.

Requires E4438C PyVISA-sim IDN and tektronix-rsa5100b on rtsa_id=1.

Run:
  colosseum run examples/test_rf_vector_mod.py --config examples/configs/bench.rf.visa-sim.toml
"""

from __future__ import annotations

import os
from pathlib import Path

import colosseum as col

_CONFIG = Path(__file__).resolve().parent / "configs" / os.environ.get(
    "COLOSSEUM_BENCH_CONFIG", "bench.rf.visa-sim.toml"
)
_WAVEFORM = Path(__file__).resolve().parent / "fixtures" / "rf" / "stub_iq.bin"


def main() -> None:
    col.config.load_config(str(_CONFIG))

    col.equipment.vsg.preset(vsg_id=1)
    col.equipment.vsg.upload_waveform(vsg_id=1, local_path=str(_WAVEFORM), remote_name="WFM1:IQ.bin")
    col.equipment.vsg.play_iq(vsg_id=1, filename="WFM1:IQ.bin", center_freq_hz=1e9, amplitude_dbm=-10.0, sample_clock_hz=100e6)
    col.equipment.vsg.set_output(vsg_id=1, enabled=True)

    col.equipment.speca.preset(speca_id=1)
    col.equipment.speca.set_reference_level(speca_id=1, level_dbm=0.0)
    col.equipment.speca.single_sweep(speca_id=1)
    col.equipment.speca.save_trace_data(speca_id=1, path="traces/modulated.csv")

    col.equipment.rtsa.set_trigger_source(rtsa_id=1, source="IMM")
    col.equipment.rtsa.run(rtsa_id=1)
    col.equipment.rtsa.save_IQ_data(rtsa_id=1, path="captures/iq.bin", file_format="bin")


if __name__ == "__main__":
    main()
    col.endex()
