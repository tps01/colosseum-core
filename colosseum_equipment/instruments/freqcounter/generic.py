from __future__ import annotations

from colosseum_equipment.protocols.scpi import SCPIHelper
from colosseum_equipment.transports.base import Transport


class GenericFreqCounter:
    """Generic SCPI frequency counter."""

    def __init__(self, transport: Transport, config: dict) -> None:
        self._scpi = SCPIHelper(transport)
        self._config = config

    def set_gate_time(self, seconds: float) -> None:
        self._scpi.write(f"SAMP:COUN {seconds}")

    def measure_frequency(self) -> float:
        return self._scpi.query_float("MEAS:FREQ?")

    def measure_period(self) -> float:
        return self._scpi.query_float("MEAS:PER?")

    def preset(self) -> None:
        self._scpi.write("*RST")

    def close(self) -> None:
        self._scpi._transport.close()
