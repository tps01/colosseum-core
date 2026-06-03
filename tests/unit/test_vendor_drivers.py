from __future__ import annotations

import pytest

from colosseum_equipment.instruments._text_protocol import parse_adaura_status_channel
from colosseum_equipment.instruments.factory import build_instrument
from colosseum_equipment.instruments.oscope.tek_t3dso2000 import _seconds_to_tdiv
from colosseum_equipment.transports.base import Transport
from colosseum_equipment.transports.null_transport import NullTransport


class _MockTransport(Transport):
    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.writes: list[str] = []
        self._responses = responses or {}

    def write(self, data: str) -> None:
        self.writes.append(data.strip())

    def read(self) -> str:
        return ""

    def query(self, data: str) -> str:
        key = data.strip()
        if key in self._responses:
            return self._responses[key]
        return self._responses.get(key.upper(), "")

    def close(self) -> None:
        return None


def test_parse_adaura_status() -> None:
    text = "Channel 1: 95.0\nChannel 2: 14.0\n"
    assert parse_adaura_status_channel(text, 1) == 95.0
    assert parse_adaura_status_channel(text, 2) == 14.0


def test_adaura_set_and_measure() -> None:
    transport = _MockTransport({"STATUS": "Channel 1: 12.5\n"})
    inst = build_instrument("attn", 1, {"model": "adaura-r3", "channel": 1}, transport)
    inst.set_attenuation_db(12.5)
    assert "SET 1 12.50" in transport.writes
    assert inst.measure_attenuation_db() == 12.5
    inst.close()


def test_seconds_to_tdiv() -> None:
    assert _seconds_to_tdiv(0.5) == "500MS"
    assert _seconds_to_tdiv(1e-6) == "1US"


def test_t3dso_measure_vpp_parse() -> None:
    transport = _MockTransport({"PAVA? CUST1": "PAVA CUST1:C1,PKPK,4.08E+00V"})
    inst = build_instrument("oscope", 1, {"model": "tektronix-t3dso2000"}, transport)
    assert inst.measure_vpp(channel=1) == pytest.approx(4.08)
    inst.close()


def test_minicircuits_set_path() -> None:
    transport = _MockTransport({"SETA=1": "1", "SETB=0": "1"})
    inst = build_instrument("rfswitch", 1, {"model": "minicircuits-rc"}, transport)
    inst.set_path("A=1;B=0")
    assert transport.query("SETA=1") == "1"
    assert transport.query("SETB=0") == "1"
    inst.close()


def test_anritsu_frequency_commands() -> None:
    transport = _MockTransport()
    inst = build_instrument("vna", 1, {"model": "anritsu-541xx", "frequency_unit": "GHz"}, transport)
    inst.set_start_frequency(8.4e9)
    inst.set_stop_frequency(12.0e9)
    assert any("ST 8.4" in w for w in transport.writes)
    assert any("SP 12" in w for w in transport.writes)
    inst.close()


@pytest.mark.parametrize(
    "kind,model",
    [
        ("eload", "itech-it8600"),
        ("eload", "chroma-8600"),
        ("eload", "agilent-6050"),
        ("freqcounter", "keysight-53220a"),
        ("freqcounter", "tektronix-fca3000"),
        ("oscope", "tektronix-mdo4000"),
        ("pwrmeter", "keysight-u2001a"),
        ("rfswitch", "minicircuits-rc"),
        ("vna", "tektronix-ttr500"),
        ("vna", "rohde-znb"),
        ("vna", "anritsu-541xx"),
    ],
)
def test_vendor_model_builds(kind: str, model: str) -> None:
    inst = build_instrument(kind, 1, {"model": model}, NullTransport())
    inst.close()
