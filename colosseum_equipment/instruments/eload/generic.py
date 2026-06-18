from __future__ import annotations

from typing import Any

from colosseum_equipment.instruments._base import ScpiInstrumentMixin
from colosseum_equipment.protocols.scpi import SCPIHelper
from colosseum_equipment.transports.base import Transport


class GenericEload(ScpiInstrumentMixin):
    """Generic SCPI electronic load."""

    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        self._scpi = SCPIHelper(transport)
        self._config = config

    def set_mode(self, mode: str) -> None:
        self._scpi.write(f"MODE {mode.upper()}")

    def set_current(self, current: float) -> None:
        self._scpi.write(f"CURR {current}")

    def set_voltage(self, voltage: float) -> None:
        self._scpi.write(f"VOLT {voltage}")

    def set_power(self, power: float) -> None:
        self._scpi.write(f"POW {power}")

    def set_resistance(self, resistance: float) -> None:
        self._scpi.write(f"RES {resistance}")

    def engage(self) -> None:
        self._scpi.write("INP ON")

    def disengage(self) -> None:
        self._scpi.write("INP OFF")

    def measure_voltage(self) -> float:
        return self._scpi.query_float("MEAS:VOLT?")

    def measure_current(self) -> float:
        return self._scpi.query_float("MEAS:CURR?")

    def preset(self) -> None:
        self._scpi.write("*RST")
