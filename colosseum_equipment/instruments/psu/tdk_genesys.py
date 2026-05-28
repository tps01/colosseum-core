from __future__ import annotations

from colosseum_equipment.instruments.psu.generic import GenericPSU
from colosseum_equipment.transports.base import Transport


class TdkGenesysPSU(GenericPSU):
    """Reference driver for TDK-Lambda Genesys (Wave 3)."""

    def __init__(self, transport: Transport, config: dict) -> None:
        super().__init__(transport, config)
        if "ovp" in config:
            self._scpi.write(f"VOLT:PROT {float(config['ovp'])}")
        if "ocp" in config:
            self._scpi.write(f"CURR:PROT {float(config['ocp'])}")
