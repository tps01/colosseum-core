from __future__ import annotations

from colosseum_equipment.protocols.scpi import SCPIHelper
from colosseum_equipment.transports.base import Transport


class GenericEload:
    """Generic SCPI electronic load."""

    def __init__(self, transport: Transport, config: dict) -> None:
        self._scpi = SCPIHelper(transport)
        self._config = config

    def set_mode(self, mode: str) -> None:
        self._scpi.write(f"MODE {mode.upper()}")

    def set_current(self, current: float) -> None:
        self._scpi.write(f"CURR {current}")

    def set_voltage(self, voltage: float) -> None:
        self._scpi.write(f"VOLT {voltage}")

    def set_input(self, enabled: bool) -> None:
        self._scpi.write("INP ON" if enabled else "INP OFF")

    def measure_voltage(self) -> float:
        return self._scpi.query_float("MEAS:VOLT?")

    def measure_current(self) -> float:
        return self._scpi.query_float("MEAS:CURR?")

    def preset(self) -> None:
        self._scpi.write("*RST")

    def close(self) -> None:
        self._scpi._transport.close()
