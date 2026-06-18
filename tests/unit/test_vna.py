"""VNA factory routing, SCPI delegation, and trace export."""

from __future__ import annotations

import csv

import pytest

from colosseum_equipment.exceptions import EquipmentCapabilityError
from colosseum_equipment.instruments.factory import build_instrument
from colosseum_equipment.instruments.vna.generic import GenericVna
from colosseum_equipment.instruments.vna.rohde_znb import RohdeZnbVna

from tests.support.stubs import RfStubTransport


def test_generic_vna_control_commands_write_scpi() -> None:
    transport = RfStubTransport({"*OPC?": "1"})
    inst = build_instrument("vna", 1, {"model": "generic"}, transport)
    assert isinstance(inst, GenericVna)

    inst.toggle_display(False)
    inst.perform_ecal("1:4")
    inst.set_marker(1, 1e9, trace=1)
    inst.set_trace_parameters(1, "S11", "MLOG")
    inst.configure_trigger("EXT", continuous=False, edge="RISE", delay_s=0.001)

    assert transport.written == [
        "SYST:DISP:UPD OFF",
        "SENS:CORR:COLL:GUID 1:4",
        "CALC:PAR1:MARK1:STAT ON",
        "CALC:MARK1:X 1000000000.000000",
        "CALC:PAR1:DEF S11",
        "CALC:PAR1:FORM MLOG",
        "TRIG:SOUR EXT",
        "INIT:CONT 0",
        "TRIG:EDGE RISE",
        "TRIG:DEL 0.001000000",
    ]


def test_rohde_vna_channel_prefixed_if_bw() -> None:
    transport = RfStubTransport()
    inst = build_instrument("vna", 1, {"model": "rohde-znb", "channel": 1}, transport)
    assert isinstance(inst, RohdeZnbVna)
    inst.set_if_bw(1000.0)
    assert transport.written == ["SENS1:BWID:RES 1000.000000"]


def test_anritsu_vna_new_methods_raise() -> None:
    inst = build_instrument("vna", 1, {"model": "anritsu-541xx", "frequency_unit": "GHz"}, RfStubTransport())
    with pytest.raises(EquipmentCapabilityError, match="toggle_display"):
        inst.toggle_display(True)


def test_save_trace_data_csv(unit_runtime_context) -> None:
    transport = RfStubTransport(
        {
            "*OPC?": "1",
            "SENS:FREQ:DATA?": "1000000000,2000000000",
            "CALC:PAR1:DATA:FDATA?": "-10.5,-12.0",
        }
    )
    inst = build_instrument("vna", 1, {"model": "generic"}, transport)
    path = inst.save_trace_data("traces/vna.csv", trace=1, file_format="csv")
    assert path.exists()
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert rows[0]["frequency_hz"] == "1000000000.000000"
    assert rows[0]["value"] == "-10.500000"


def test_save_trace_data_s2p(unit_runtime_context) -> None:
    transport = RfStubTransport(
        {
            "*OPC?": "1",
            "SENS:FREQ:DATA?": "1000000000,2000000000",
            "CALC:PAR1:DATA:SDATA?": "1.0,0.0,0.5,0.1",
        }
    )
    inst = build_instrument("vna", 1, {"model": "generic"}, transport)
    path = inst.save_trace_data("traces/vna.s2p", trace=1, file_format="s2p", parameter="S11")
    text = path.read_text(encoding="utf-8")
    assert "# Hz S RI R 50" in text
    assert "1000000000.000000 1.000000 0.000000" in text
    assert "2000000000.000000 0.500000 0.100000" in text
