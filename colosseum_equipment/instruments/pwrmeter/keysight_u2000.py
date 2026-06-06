"""Keysight / Agilent U2000-series USB power sensors (U2001A, etc.).

Commands per U2000 Series Programming Guide (U2000-90411): ``SENS:FREQ``,
``SENS:AVER:COUN``, ``FETCh?``, ``CAL:ZERO:AUTO ONCE``.
Operating guide: Keysight U2001A specs/manual PDF in repo docs.
"""

from __future__ import annotations

from colosseum_equipment.instruments.pwrmeter.generic import GenericPwrMeter


class KeysightU2000PwrMeter(GenericPwrMeter):
    def set_frequency(self, frequency_hz: float) -> None:
        self._scpi.write(f"SENS:FREQ {frequency_hz:.6f}")

    def set_averaging_count(self, count: int) -> None:
        self._scpi.write(f"SENS:AVER:COUN {int(count)}")

    def measure_power(self) -> float:
        return self._scpi.query_float("FETCh?")

    def zero_sensor(self) -> None:
        self._scpi.write("CAL:ZERO:AUTO ONCE")
