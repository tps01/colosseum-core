from __future__ import annotations

from typing import Any

from colosseum_equipment.instruments._base import ScpiInstrumentMixin
from colosseum_equipment.protocols.scpi import SCPIHelper
from colosseum_equipment.transports.base import Transport


class GenericPwrMeter(ScpiInstrumentMixin):
    """Generic SCPI RF power meter."""

    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        self._scpi = SCPIHelper(transport)
        self._config = config
        if "frequency" in config:
            self.set_frequency(float(config["frequency"]))

    def set_frequency(self, frequency_hz: float) -> None:
        self._scpi.write(f"FREQ {frequency_hz:.6f}")

    def set_averaging_count(self, count: int) -> None:
        self._scpi.write(f"AVER:COUN {int(count)}")

    def measure_power(self) -> float:
        return self._scpi.query_float("MEAS:POW?")

    def zero_sensor(self) -> None:
        self._scpi.write("CAL:ZERO")

    def preset(self) -> None:
        self._scpi.write("*RST")
