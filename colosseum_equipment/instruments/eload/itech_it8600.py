"""Itech IT8600 series electronic load (SCPI).

Manual: IT8600 Programming Guide — ``CURRent:LEVel``, ``FUNCtion``, ``INPut:STATe``.
"""

from __future__ import annotations

from colosseum_equipment.instruments.eload.generic import GenericEload


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

    def set_power(self, power: float) -> None:
        self._scpi.write(f"POWer:LEVel {power}")

    def set_resistance(self, resistance: float) -> None:
        self._scpi.write(f"RESistance:LEVel {resistance}")

    def engage(self) -> None:
        self._scpi.write("INPut:STATe ON")

    def disengage(self) -> None:
        self._scpi.write("INPut:STATe OFF")

    def measure_voltage(self) -> float:
        return self._scpi.query_float("MEASure:VOLTage?")

    def measure_current(self) -> float:
        return self._scpi.query_float("MEASure:CURRent?")
