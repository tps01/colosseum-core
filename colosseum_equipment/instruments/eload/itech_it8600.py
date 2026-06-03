"""Itech IT8600 series electronic load (SCPI).

Manual: IT8600 Programming Guide — ``CURRent:LEVel``, ``FUNCtion``, ``INPut:STATe``.
"""

from __future__ import annotations

from colosseum_equipment.instruments.eload.generic import GenericEload
from colosseum_equipment.transports.base import Transport


class ItechIT8600Eload(GenericEload):
    _MODE_MAP = {
        "cc": "CURRent",
        "cv": "VOLTage",
        "cr": "RESistance",
        "cp": "POWer",
    }

    def set_mode(self, mode: str) -> None:
        func = self._MODE_MAP.get(mode.lower(), mode)
        self._scpi.write(f"FUNCtion {func}")

    def set_current(self, current: float) -> None:
        self._scpi.write(f"CURRent:LEVel {current}")

    def set_voltage(self, voltage: float) -> None:
        self._scpi.write(f"VOLTage:LEVel {voltage}")

    def set_input(self, enabled: bool) -> None:
        self._scpi.write(f"INPut:STATe {'ON' if enabled else 'OFF'}")

    def measure_voltage(self) -> float:
        return self._scpi.query_float("MEASure:VOLTage?")

    def measure_current(self) -> float:
        return self._scpi.query_float("MEASure:CURRent?")
