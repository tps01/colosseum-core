"""Keysight 53220A/53230A frequency counter (SCPI).

Manual: Keysight 53220A/53230A User's Guide — ``MEASure:FREQuency?``, gate time.
"""

from __future__ import annotations

from colosseum_equipment.instruments.freqcounter.generic import GenericFreqCounter
from colosseum_equipment.transports.base import Transport


class Keysight53220AFreqCounter(GenericFreqCounter):
    def set_gate_time(self, seconds: float) -> None:
        self._scpi.write(f"SENSe:FREQuency:GATE:TIME {seconds}")

    def measure_frequency(self) -> float:
        return self._scpi.query_float("MEASure:FREQuency?")

    def measure_period(self) -> float:
        return self._scpi.query_float("MEASure:PERiod?")
