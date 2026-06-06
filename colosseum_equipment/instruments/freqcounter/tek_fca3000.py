"""Tektronix FCA3000/FCA3100/MCA3000 timer/counter (SCPI).

Manual: 077-0494-00 Programmer Manual — frequency measurement subsystem.
"""

from __future__ import annotations

from colosseum_equipment.instruments.freqcounter.generic import GenericFreqCounter


class TekFca3000FreqCounter(GenericFreqCounter):
    def set_gate_time(self, seconds: float) -> None:
        self._scpi.write(f"SENSe:FREQuency:GATE:TIME {seconds}")

    def measure_frequency(self) -> float:
        self._scpi.write(":FUNC 'FREQ'")
        return self._scpi.query_float("MEASure:FREQuency?")

    def measure_period(self) -> float:
        self._scpi.write(":FUNC 'PER'")
        return self._scpi.query_float("MEASure:PERiod?")
