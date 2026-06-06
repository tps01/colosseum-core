"""Electronic load factory routing and SCPI delegation."""

from __future__ import annotations

from colosseum_equipment.instruments.eload.agilent_6050 import Agilent6050Eload
from colosseum_equipment.instruments.eload.chroma_8600 import Chroma8600Eload
from colosseum_equipment.instruments.eload.generic import GenericEload
from colosseum_equipment.instruments.eload.itech_it8600 import ItechIT8600Eload
from colosseum_equipment.instruments.factory import build_instrument

from tests.support.stubs import RfStubTransport


def test_generic_eload_setters_write_scpi() -> None:
    transport = RfStubTransport()
    inst = build_instrument("eload", 1, {"model": "generic"}, transport)
    assert isinstance(inst, GenericEload)

    inst.set_power(50.0)
    inst.set_resistance(100.0)
    inst.engage()
    inst.disengage()

    assert transport.written == [
        "POW 50.0",
        "RES 100.0",
        "INP ON",
        "INP OFF",
    ]


def test_chroma_eload_vendor_scpi() -> None:
    transport = RfStubTransport()
    inst = build_instrument("eload", 1, {"model": "chroma-8600"}, transport)
    assert isinstance(inst, Chroma8600Eload)

    inst.set_power(25.0)
    inst.set_resistance(50.0)
    inst.engage()
    inst.disengage()

    assert transport.written == [
        "POW:LEV 25.0",
        "RES:LEV 50.0",
        "INP 1",
        "INP 0",
    ]


def test_itech_eload_vendor_scpi() -> None:
    transport = RfStubTransport()
    inst = build_instrument("eload", 1, {"model": "itech-it8600"}, transport)
    assert isinstance(inst, ItechIT8600Eload)

    inst.set_power(10.0)
    inst.set_resistance(200.0)
    inst.engage()
    inst.disengage()

    assert transport.written == [
        "POWer:LEVel 10.0",
        "RESistance:LEVel 200.0",
        "INPut:STATe ON",
        "INPut:STATe OFF",
    ]


def test_agilent_eload_engage_disengage() -> None:
    transport = RfStubTransport()
    inst = build_instrument("eload", 1, {"model": "agilent-6050"}, transport)
    assert isinstance(inst, Agilent6050Eload)

    inst.engage()
    inst.disengage()

    assert transport.written == [
        "INPUT ON",
        "INPUT OFF",
    ]
