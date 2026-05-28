from __future__ import annotations

from colosseum_equipment.instruments.dmm.generic import GenericDMM
from colosseum_equipment.transports.base import Transport


class KeysightEDU34450A(GenericDMM):
    """Reference driver for Keysight EDU34450A (Wave 3)."""

    def measure_voltage(self, channel: int) -> float:
        self._scpi.write(f"CONF:VOLT:DC CH{channel}")
        return self._scpi.query_float("READ?")
