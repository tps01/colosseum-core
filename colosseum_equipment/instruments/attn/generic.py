from __future__ import annotations

from typing import Any

from colosseum_equipment.instruments._base import ScpiInstrumentMixin
from colosseum_equipment.protocols.scpi import SCPIHelper
from colosseum_equipment.transports.base import Transport


class GenericAttn(ScpiInstrumentMixin):
    """Generic SCPI digital step attenuator (best-effort ``ATT`` commands)."""

    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        self._scpi = SCPIHelper(transport)
        self._config = config
        if "attenuation_db" in config:
            self.set_attenuation_db(float(config["attenuation_db"]))

    def set_attenuation_db(self, attenuation_db: float) -> None:
        self._scpi.write(f"ATT {attenuation_db:.3f}")

    def measure_attenuation_db(self) -> float:
        return self._scpi.query_float("ATT?")

    def preset(self) -> None:
        self._scpi.write("*RST")
