"""SpecA SCPI delegation, bandwidth calculation, and trace plot artifacts."""

from __future__ import annotations

import csv

import pytest

from colosseum_equipment.instruments.factory import build_instrument
from colosseum_equipment.instruments.speca.bandwidth import measure_bandwidth_hz
from colosseum_equipment.instruments.speca.generic import GenericSpecA
from colosseum_equipment.instruments.speca.keysight_e4407b import KeysightE4407BSpecA
from colosseum_equipment.instruments.speca.trace_csv import frequency_axis, write_trace_csv

from tests.support.stubs import RfStubTransport


def test_generic_speca_control_commands_write_scpi() -> None:
    transport = RfStubTransport({"*OPC?": "1"})
    inst = build_instrument("speca", 1, {"model": "generic"}, transport)
    assert isinstance(inst, GenericSpecA)

    inst.set_start_frequency(1.0e9)
    inst.set_stop_frequency(2.0e9)
    inst.toggle_marker(1, True)
    inst.toggle_marker(2, False)
    inst.next_peak_right(1)
    inst.next_peak_left(1)
    inst.next_highest_peak(1)
    inst.set_sweep_points(801)
    inst.toggle_trigger_delay(True)
    inst.set_trigger_delay(0.001)
    inst.set_trigger_source("EXT")
    inst.user_preset()

    assert transport.written == [
        "FREQ:STAR 1000000000.000000",
        "FREQ:STOP 2000000000.000000",
        "CALC:MARK1:STAT ON",
        "CALC:MARK2:STAT OFF",
        "CALC:MARK1:MAX:NEXT",
        "CALC:MARK1:MAX:PREV",
        "CALC:MARK1:MAX",
        "SWE:POIN 801",
        "TRIG:DEL:STAT ON",
        "TRIG:DEL 0.001000000",
        "TRIG:SOUR EXT",
        "*RCL 1",
    ]


def test_keysight_e4407b_start_stop_and_sweep_points() -> None:
    transport = RfStubTransport()
    inst = build_instrument("speca", 1, {"model": "keysight-e4407b"}, transport)
    assert isinstance(inst, KeysightE4407BSpecA)

    inst.set_start_frequency(1.0e9)
    inst.set_stop_frequency(2.0e9)
    inst.set_sweep_points(401)

    assert transport.written == [
        "SENS:FREQ:STAR 1000000000.000000",
        "SENS:FREQ:STOP 2000000000.000000",
        "SENS:SWE:POIN 401",
    ]


def test_measure_bandwidth_hz_flat_top_trace() -> None:
    center_hz = 1.5e9
    span_hz = 200e6
    count = 201
    frequencies = frequency_axis(center_hz, span_hz, count)
    amplitudes = [-50.0 if frequency < 1.45e9 or frequency > 1.55e9 else -10.0 for frequency in frequencies]

    bandwidth_hz = measure_bandwidth_hz(
        frequencies,
        amplitudes,
        start_hz=1.4e9,
        stop_hz=1.6e9,
        threshold_db=3.0,
    )
    assert bandwidth_hz == pytest.approx(100e6, rel=0.01)


def test_save_trace_data_csv_only(unit_runtime_context) -> None:
    transport = RfStubTransport(
        {
            "*OPC?": "1",
            "FREQ:CENT?": "1500000000.0",
            "FREQ:SPAN?": "200000000.0",
            "TRAC:DATA? TRACE1": "-10.0,-20.0,-30.0",
        }
    )
    inst = build_instrument("speca", 1, {"model": "generic"}, transport)
    csv_path = inst.save_trace_data("traces/speca.csv", save_plot=False)

    assert csv_path.exists()
    assert not csv_path.with_suffix(".png").exists()
    with csv_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 3
    assert rows[0]["frequency_hz"] == "1400000000.000000"
    assert rows[0]["amplitude_dbm"] == "-10.000000"


@pytest.mark.plot
def test_save_trace_data_with_plot(unit_runtime_context) -> None:
    transport = RfStubTransport(
        {
            "*OPC?": "1",
            "FREQ:CENT?": "1500000000.0",
            "FREQ:SPAN?": "200000000.0",
            "TRAC:DATA? TRACE1": "-10.0,-20.0,-30.0",
        }
    )
    inst = build_instrument("speca", 1, {"model": "generic"}, transport)
    csv_path = inst.save_trace_data("traces/speca.csv", save_plot=True)
    plot_path = csv_path.with_suffix(".png")

    assert csv_path.exists()
    assert plot_path.exists()
    with csv_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 3
    assert rows[0]["frequency_hz"] == "1400000000.000000"
    assert rows[0]["amplitude_dbm"] == "-10.000000"
