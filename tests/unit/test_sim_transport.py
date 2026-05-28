"""U-EQ-01: SimTransport SCPI contract."""

from __future__ import annotations

import pytest

from colosseum.context import init_context
from colosseum_equipment.transports.sim import SimTransport


def test_psu_voltage_query_tracks_writes(isolated_cwd) -> None:
    init_context(test_case_name="sim")
    psu = SimTransport("psu", 1, {"voltage": 3.3})
    psu.write("VOLT 5.0")
    psu.write("OUTP ON")
    assert float(psu.query("VOLT?")) == pytest.approx(5.0)


def test_dmm_reads_psu1_voltage_when_output_enabled(isolated_cwd) -> None:
    init_context(test_case_name="sim")
    psu = SimTransport("psu", 1, {"voltage": 3.3})
    psu.write("VOLT 3.3")
    psu.write("OUTP ON")
    dmm = SimTransport("dmm", 1, {})
    reading = float(dmm.query("READ?"))
    assert reading == pytest.approx(3.3, rel=1e-3)
