"""Unit tests for autoconfig *IDN? classification."""

from __future__ import annotations

from colosseum_equipment.autoconfig.idn_registry import classify_idn


def test_tier1_vendor_models() -> None:
    match = classify_idn("Keysight Technologies,EDU34450A,MY123,1.0.0")
    assert match is not None
    assert match.kind == "dmm"
    assert match.model == "keysight-edu34450a"

    match = classify_idn("TDK-Lambda,GENESYS-28-80,1,1.2")
    assert match is not None
    assert match.kind == "psu"
    assert match.model == "tdk-genesys"

    match = classify_idn("Agilent Technologies,E4438C,US0001,1.0")
    assert match is not None
    assert match.kind == "vsg"
    assert match.model == "keysight-esg"


def test_tier2_generic_heuristics() -> None:
    match = classify_idn("ACME,DMM-1000,1,1")
    assert match is not None
    assert match.kind == "dmm"
    assert match.model == "generic"


def test_unknown_idn_returns_none() -> None:
    assert classify_idn("UNKNOWN,WIDGET,1,1") is None
    assert classify_idn("") is None
