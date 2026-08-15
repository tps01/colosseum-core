"""Vendor model routing (unit-level, no I/O)."""

from __future__ import annotations

import pytest
from colosseum_equipment.instruments.dmm.keysight_edu34450a import KeysightEDU34450A
from colosseum_equipment.instruments.factory import build_instrument
from colosseum_equipment.instruments.psu.tdk_genesys import TdkGenesysPSU
from colosseum_equipment.instruments.registry import registered_kinds
from tests.support.stubs import StubTransport


def test_keysight_dmm_model() -> None:
    inst = build_instrument("dmm", 1, {"model": "keysight-edu34450a"}, StubTransport())
    assert isinstance(inst, KeysightEDU34450A)


def test_tdk_psu_model() -> None:
    inst = build_instrument("psu", 1, {"model": "tdk-genesys", "ovp": 5.0}, StubTransport())
    assert isinstance(inst, TdkGenesysPSU)


def test_unsupported_model_raises() -> None:
    with pytest.raises(RuntimeError, match="Unsupported equipment model"):
        build_instrument("dmm", 1, {"model": "unknown-vendor"}, StubTransport())


def test_builtin_registration_covers_existing_equipment_kinds() -> None:
    assert registered_kinds() >= {
        "asg",
        "attn",
        "dmm",
        "eload",
        "freqcounter",
        "oscope",
        "psu",
        "pwrmeter",
        "rfswitch",
        "rtsa",
        "speca",
        "vna",
        "vsg",
    }
