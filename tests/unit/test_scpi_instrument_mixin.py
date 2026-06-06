"""ScpiInstrumentMixin close behavior."""

from __future__ import annotations

from colosseum_equipment.instruments.dmm.generic import GenericDMM
from tests.support.stubs import StubTransport


class _ClosingStubTransport(StubTransport):
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_generic_dmm_mixin_close() -> None:
    transport = _ClosingStubTransport()
    GenericDMM(transport).close()
    assert transport.closed is True
