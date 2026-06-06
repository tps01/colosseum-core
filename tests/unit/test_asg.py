"""Analog signal generator factory routing and SCPI delegation."""

from __future__ import annotations

from colosseum_equipment.instruments.asg.generic import GenericASG
from colosseum_equipment.instruments.factory import build_instrument

from tests.support.stubs import RfStubTransport


def test_generic_asg_model() -> None:
    inst = build_instrument("asg", 1, {"model": "generic"}, RfStubTransport())
    assert isinstance(inst, GenericASG)


def test_generic_asg_setters_write_scpi() -> None:
    transport = RfStubTransport()
    inst = build_instrument("asg", 1, {"model": "generic"}, transport)

    inst.set_frequency(2.4e9)
    inst.set_power(-10.0)
    inst.set_output(True)
    inst.set_pulsegen_output(True)
    inst.set_pulsemod_output(False)
    inst.set_pulse_period(0.001)
    inst.set_pulse_width(0.0001)

    assert transport.written == [
        "FREQ:CW 2400000000.000000",
        "POW:AMPL -10.000",
        "OUTP ON",
        ":PULGen:STAT ON",
        ":PULM:STAT OFF",
        ":PULM:PER 0.001000000",
        ":PULM:WIDt 0.000100000",
    ]


def test_generic_asg_config_bootstrap() -> None:
    transport = RfStubTransport()
    build_instrument(
        "asg",
        1,
        {"model": "generic", "frequency": 1e9, "power_dbm": -5.0, "output": True},
        transport,
    )
    assert transport.written == [
        "FREQ:CW 1000000000.000000",
        "POW:AMPL -5.000",
        "OUTP ON",
    ]
