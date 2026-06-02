"""Agilent 6050/6060 electronic load family (SCPI).

Manual: Agilent 06060-90005 Programming Manual — ``CURR``, ``VOLT``, ``INPUT``, ``MEAS:CURR?``.
"""

from __future__ import annotations

from colosseum_equipment.instruments.eload.generic import GenericEload
from colosseum_equipment.transports.base import Transport


class Agilent6050Eload(GenericEload):
    def set_mode(self, mode: str) -> None:
        self._scpi.write(f"MODE:{mode.upper()}")

    def set_current(self, current: float) -> None:
        self._scpi.write(f"CURR {current}")

    def set_voltage(self, voltage: float) -> None:
        self._scpi.write(f"VOLT {voltage}")

    def set_input(self, enabled: bool) -> None:
        self._scpi.write("INPUT ON" if enabled else "INPUT OFF")

    def measure_voltage(self) -> float:
        return self._scpi.query_float("MEAS:VOLT?")

    def measure_current(self) -> float:
        return self._scpi.query_float("MEAS:CURR?")
