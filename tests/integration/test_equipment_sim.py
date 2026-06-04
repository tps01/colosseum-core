"""I-EQ: equipment plugin on sim transport."""

from __future__ import annotations

import colosseum as col
from colosseum.config import load_config

from tests.support.helpers import run_endex_expect_code


def test_power_rail_measure_and_verify_pass(bench_sim, isolated_cwd) -> None:
    load_config(bench_sim)
    col.equipment.psu.set_voltage(psu_id=1, voltage=3.3)
    col.equipment.psu.set_output(psu_id=1, enabled=True)
    col.equipment.dmm.measure_voltage(dmm_id=1, channel=1, key="vrail_3v3")
    result = col.equipment.dmm.verify_voltage(key="vrail_3v3", expected_val=3.3, tolerance=0.1)
    assert result.status == "PASS"
    readback = col.equipment.scpi.query_float(psu_id=1, command="VOLT?")
    assert readback >= 3.0
    run_endex_expect_code(0)


def test_scpi_query_float_reflects_psu_state(bench_sim, isolated_cwd) -> None:
    load_config(bench_sim)
    col.equipment.psu.set_voltage(psu_id=1, voltage=4.0)
    value = col.equipment.scpi.query_float(psu_id=1, command="VOLT?")
    assert abs(value - 4.0) < 0.01
