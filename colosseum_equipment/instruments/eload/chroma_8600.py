"""Chroma / programmable DC load 8600 series (SCPI).

Manual: 8600 Series Programming Manual — ``FUNCtion``, ``CURRent:LEVel``, ``INPut:STATe``.
"""

from __future__ import annotations

from colosseum_equipment.instruments.eload.generic import GenericEload
from colosseum_equipment.transports.base import Transport


class Chroma8600Eload(GenericEload):
    _MODE_MAP = {
        "cc": "CURRent",
        "cv": "VOLTage",
        "cr": "RESistance",
        "cp": "POWer",
    }

    def set_mode(self, mode: str) -> None:
        func = self._MODE_MAP.get(mode.lower(), mode)
        self._scpi.write(f"FUNC {func}")

    def set_current(self, current: float) -> None:
        self._scpi.write(f"CURR:LEV {current}")

    def set_voltage(self, voltage: float) -> None:
        self._scpi.write(f"VOLT {voltage}")

    def set_input(self, enabled: bool) -> None:
        self._scpi.write(f"INP {1 if enabled else 0}")

    def measure_voltage(self) -> float:
        return self._scpi.query_float("MEAS:VOLT?")

    def measure_current(self) -> float:
        return self._scpi.query_float("MEAS:CURR?")
