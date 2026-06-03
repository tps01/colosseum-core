"""Integration tests for RF equipment via PyVISA-sim."""

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
BENCH_RF = REPO / "examples" / "configs" / "bench.rf.visa-sim.toml"


@pytest.fixture
def bench_rf(repo_root: Path) -> Path:
    assert BENCH_RF.is_file()
    return BENCH_RF


def test_load_config_rf_bench(bench_rf, isolated_cwd) -> None:
    pytest.importorskip("pyvisa_sim")
    store = load_config(bench_rf)
    vsg = store.list_items("equipment.vsg")
    speca = store.list_items("equipment.speca")
    assert vsg and vsg[0].get("model") == "keysight-esg"
    assert "driver" not in vsg[0]
    assert len(speca) == 2


def test_vsg_set_frequency_and_output(bench_rf, isolated_cwd) -> None:
    pytest.importorskip("pyvisa_sim")
    from colosseum_equipment.api import scpi, vsg

    load_config(bench_rf)
    vsg.set_frequency(vsg_id=1, frequency=2.4e9)
    vsg.set_power(vsg_id=1, power_dbm=-5.0)
    vsg.set_output(vsg_id=1, enabled=True)
    assert float(scpi.query(command="FREQ:CW?", vsg_id=1)) == pytest.approx(2.4e9)
    assert float(scpi.query(command="OUTP:STAT?", vsg_id=1)) == pytest.approx(1.0)


def test_speca_peak_and_marker_power(bench_rf, isolated_cwd) -> None:
    pytest.importorskip("pyvisa_sim")
    from colosseum_equipment.api import speca

    load_config(bench_rf)
    speca.set_center_frequency(speca_id=1, frequency=1e9)
    speca.peak_search(speca_id=1, marker=1)
    power = speca.measure_marker_power(speca_id=1, marker=1, key="carrier")
    assert power == pytest.approx(-42.5, rel=1e-3)


def test_speca_marker_at_frequency_and_verify(bench_rf, isolated_cwd) -> None:
    pytest.importorskip("pyvisa_sim")
    from colosseum_equipment.api import speca

    load_config(bench_rf)
    speca.set_marker_frequency(speca_id=1, marker=1, frequency_hz=1e9)
    speca.measure_marker_power(speca_id=1, marker=1, key="marker_1ghz")
    result = speca.verify_marker_power(key="marker_1ghz", expected_val=-42.5, tolerance=0.5)
    assert result.status == "PASS"


def test_speca_trace_power_at_frequency_and_verify(bench_rf, isolated_cwd) -> None:
    pytest.importorskip("pyvisa_sim")
    from colosseum_equipment.api import speca

    load_config(bench_rf)
    speca.save_trace_data(speca_id=1, path="traces/verify.csv")
    speca.measure_trace_power_at_frequency(speca_id=1, frequency_hz=1e9, key="trace_1ghz")
    result = speca.verify_trace_power_at_frequency(key="trace_1ghz", expected_val=-41.0, tolerance=0.5)
    assert result.status == "PASS"


def test_speca_save_trace_data(bench_rf, isolated_cwd) -> None:
    pytest.importorskip("pyvisa_sim")
    from colosseum_equipment.api import speca

    load_config(bench_rf)
    speca.save_trace_data(speca_id=1, path="traces/carrier.csv")
    trace_files = list(Path.cwd().glob("outputs/*/traces/carrier.csv"))
    assert trace_files
    content = trace_files[0].read_text(encoding="utf-8")
    assert "frequency_hz" in content
    assert "-42.5" in content


def test_tek_speca_center_span(bench_rf, isolated_cwd) -> None:
    pytest.importorskip("pyvisa_sim")
    from colosseum_equipment.api import scpi, speca

    load_config(bench_rf)
    speca.set_center_frequency(speca_id=2, frequency=2.5e9)
    speca.set_span(speca_id=2, span=20e6)
    assert float(scpi.query(command="DISP:SPEC:FREQ:OFFS?", speca_id=2)) == pytest.approx(2.5e9)
    assert float(scpi.query(command="DISP:SPEC:FREQ:SCAL?", speca_id=2)) == pytest.approx(20e6)
