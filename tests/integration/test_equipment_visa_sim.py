"""Integration tests using PyVISA-sim (driver=visa, visa_backend=sim)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from colosseum.config import load_config

pytestmark = [
    pytest.mark.visa_sim,
    pytest.mark.skipif(sys.version_info < (3, 10), reason="pyvisa-sim requires Python 3.10+"),
]

REPO = Path(__file__).resolve().parents[2]
BENCH_VISA_SIM = REPO / "examples" / "configs" / "bench.visa-sim.toml"


@pytest.fixture
def bench_visa_sim(repo_root: Path) -> Path:
    assert BENCH_VISA_SIM.is_file()
    return BENCH_VISA_SIM


def test_load_config_visa_sim_bench(bench_visa_sim, isolated_cwd) -> None:
    pytest.importorskip("pyvisa_sim")
    store = load_config(bench_visa_sim)
    psus = store.list_items("equipment.psu")
    assert psus and psus[0].get("visa_backend") == "sim"
    dmms = store.list_items("equipment.dmm")
    assert dmms and dmms[0].get("sim_definition")


def test_psu_set_voltage_and_query_scpi(bench_visa_sim, isolated_cwd) -> None:
    pytest.importorskip("pyvisa_sim")
    from colosseum_equipment.api import psu, scpi

    load_config(bench_visa_sim)
    psu.set_voltage(psu_id=1, voltage=5.0)
    reading = float(scpi.query(command="VOLT?", psu_id=1))
    assert reading == pytest.approx(5.0)


def test_dmm_measure_voltage(bench_visa_sim, isolated_cwd) -> None:
    pytest.importorskip("pyvisa_sim")
    from colosseum_equipment.api import dmm

    load_config(bench_visa_sim)
    value = dmm.measure_voltage(dmm_id=1, channel=1, key="visa_sim_rail")
    assert value == pytest.approx(3.3, rel=1e-3)
