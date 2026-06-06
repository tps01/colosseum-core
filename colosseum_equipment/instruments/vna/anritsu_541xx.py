"""Anritsu 541XXA network analyzer (GPIB mnemonics).

Manual: 10410-00147 GPIB User's Guide — ``ST``/``SP``/``DP``/``SUS`` (not SCPI).
Operation context: 10410-00141 Operation Manual.
"""

from __future__ import annotations

from typing import Any

from colosseum_equipment.instruments.vna.generic import GenericVna
from colosseum_equipment.transports.base import Transport

# GPIB DP code -> approximate point count (541XXA display resolution)
_DP_BY_POINTS = {
    51: 5,
    101: 1,
    201: 2,
    401: 4,
}


class Anritsu541xxVna(GenericVna):
    _model = "anritsu-541xx"

    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        super().__init__(transport, config)
        self._transport = transport
        self._model = str(config.get("model", "anritsu-541xx")).lower()
        unit = str(config.get("frequency_unit", "GHz")).upper()
        if unit not in ("GHZ", "MHZ"):
            raise ValueError("frequency_unit must be GHz or MHz")
        self._frequency_unit = unit

    def _format_freq(self, frequency_hz: float) -> str:
        if self._frequency_unit == "MHZ":
            return f"{frequency_hz / 1e6:g}"
        return f"{frequency_hz / 1e9:g}"

    def preset(self) -> None:
        self._transport.write("SSM")

    def set_start_frequency(self, frequency_hz: float) -> None:
        self._transport.write(f"ST {self._format_freq(frequency_hz)}")

    def set_stop_frequency(self, frequency_hz: float) -> None:
        self._transport.write(f"SP {self._format_freq(frequency_hz)}")

    def set_points(self, count: int) -> None:
        dp_code = 2
        for points, code in _DP_BY_POINTS.items():
            if count <= points:
                dp_code = code
                break
        else:
            dp_code = 4
        self._transport.write(f"DP {dp_code}")

    def single_sweep(self) -> None:
        self._transport.write("SUS 1")

    def wait_complete(self) -> None:
        self._transport.query("*OPC?")
