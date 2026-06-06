from __future__ import annotations

import colosseum as col


def test_psu_verify_voltage_sim() -> None:
    col.config.load_config("examples/configs/bench.sim.toml")
    col.equipment.psu.set_voltage(psu_id=1, voltage=3.3)
    col.equipment.psu.set_output(psu_id=1, enabled=True)
    col.equipment.psu.measure_voltage(psu_id=1, key="psu_v")
    result = col.equipment.psu.verify_voltage(key="psu_v", expected_val=3.3, tolerance=0.2)
    assert result.status == "PASS"
    assert result.actual is not None
    rows = col.database.read_verifications()
    assert rows[-1].actual is not None
