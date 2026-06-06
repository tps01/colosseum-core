"""Instrument model registry."""

from __future__ import annotations

import pytest

from colosseum_equipment.instruments.registry import build_registered, registered_kinds
from tests.support.stubs import StubTransport


def test_registered_kinds_include_core_bench_types() -> None:
    kinds = registered_kinds()
    assert {"dmm", "psu", "vsg", "asg", "speca", "rtsa", "vna"}.issubset(kinds)


def test_build_registered_generic_dmm() -> None:
    from colosseum_equipment.instruments.dmm.generic import GenericDMM

    instrument = build_registered("dmm", "generic", StubTransport(), {})
    assert isinstance(instrument, GenericDMM)


def test_build_registered_unknown_model_raises() -> None:
    with pytest.raises(RuntimeError, match="Unsupported equipment model"):
        build_registered("dmm", "not-a-real-model", StubTransport(), {})
