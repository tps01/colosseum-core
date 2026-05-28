from __future__ import annotations

from colosseum_equipment.protocols.scpi import SCPIHelper
from colosseum_equipment.transports.base import Transport


class GenericDMM:
    def __init__(self, transport: Transport) -> None:
        self._scpi = SCPIHelper(transport)

    def measure_voltage(self, channel: int) -> float:
        _ = channel
        self._scpi.write("CONF:VOLT:DC")
        return self._scpi.query_float("READ?")

    def close(self) -> None:
        self._scpi._transport.close()
