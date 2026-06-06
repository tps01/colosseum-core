from __future__ import annotations

from colosseum_equipment.instruments.dmm.generic import GenericDMM


class KeysightEDU34450A(GenericDMM):
    """Reference driver for Keysight EDU34450A (Keysight EDU34450A Programming Guide)."""

    def measure_voltage(self, channel: int) -> float:
        self._scpi.write(f"CONF:VOLT:DC CH{channel}")
        return self._scpi.query_float("READ?")

    def measure_current(self, channel: int) -> float:
        self._scpi.write(f"CONF:CURR:DC CH{channel}")
        return self._scpi.query_float("READ?")

    def measure_resistance(self, channel: int) -> float:
        self._scpi.write(f"CONF:RES CH{channel}")
        return self._scpi.query_float("READ?")
