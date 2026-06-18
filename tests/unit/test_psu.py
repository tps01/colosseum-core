"""PSU control and wait helpers."""

from __future__ import annotations

import pytest

from colosseum_equipment.exceptions import EquipmentTimeoutError
from colosseum_equipment.instruments.factory import build_instrument

from tests.support.stubs import RfStubTransport


class _CurrentRampTransport(RfStubTransport):
    def __init__(self, readings: list[float]) -> None:
        super().__init__()
        self._readings = list(readings)
        self._index = 0

    def query(self, data: str) -> str:
        if data.strip() == "MEAS:CURR?":
            if self._index < len(self._readings):
                value = self._readings[self._index]
                self._index += 1
                return str(value)
            return str(self._readings[-1])
        return super().query(data)


def test_wait_for_current_reaches_target() -> None:
    transport = _CurrentRampTransport([0.1, 0.5, 0.95, 1.0])
    inst = build_instrument("psu", 1, {"model": "generic"}, transport)
    inst.wait_for_current(1.0, timeout_s=1.0, tolerance=0.05)


def test_wait_for_current_times_out() -> None:
    transport = _CurrentRampTransport([0.1, 0.2, 0.2])
    inst = build_instrument("psu", 1, {"model": "generic"}, transport)
    with pytest.raises(EquipmentTimeoutError, match="did not reach"):
        inst.wait_for_current(1.0, timeout_s=0.2, tolerance=0.01)
