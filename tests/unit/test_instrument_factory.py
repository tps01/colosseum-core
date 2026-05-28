"""Vendor model routing (unit-level, no I/O)."""

from __future__ import annotations

from colosseum_equipment.instruments.dmm.keysight_edu34450a import KeysightEDU34450A
from colosseum_equipment.instruments.factory import build_instrument
from colosseum_equipment.instruments.psu.tdk_genesys import TdkGenesysPSU
class _StubTransport:
    def write(self, data: str) -> None:
        pass

    def query(self, data: str) -> str:
        return "0"

    def close(self) -> None:
        pass


def test_keysight_dmm_model() -> None:
    inst = build_instrument("dmm", 1, {"model": "keysight-edu34450a"}, _StubTransport())
    assert isinstance(inst, KeysightEDU34450A)


def test_tdk_psu_model() -> None:
    inst = build_instrument("psu", 1, {"model": "tdk-genesys", "ovp": 5.0}, _StubTransport())
    assert isinstance(inst, TdkGenesysPSU)


def test_unsupported_model_raises() -> None:
    import pytest

    with pytest.raises(RuntimeError, match="Unsupported equipment model"):
        build_instrument("dmm", 1, {"model": "unknown-vendor"}, _StubTransport())
