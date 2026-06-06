from __future__ import annotations

from colosseum_equipment.instruments._base import ScpiInstrumentMixin
from colosseum_equipment.protocols.scpi import SCPIHelper
from colosseum_equipment.transports.base import Transport


class GenericDMM(ScpiInstrumentMixin):
    def __init__(self, transport: Transport) -> None:
        self._scpi = SCPIHelper(transport)

    def measure_voltage(self, channel: int) -> float:
        _ = channel
        self._scpi.write("CONF:VOLT:DC")
        return self._scpi.query_float("READ?")

    def measure_current(self, channel: int) -> float:
        _ = channel
        self._scpi.write("CONF:CURR:DC")
        return self._scpi.query_float("READ?")

    def measure_resistance(self, channel: int) -> float:
        _ = channel
        self._scpi.write("CONF:RES")
        return self._scpi.query_float("READ?")
