from __future__ import annotations

from colosseum_equipment.instruments.registry import register

from .generic import GenericPSU
from .tdk_genesys import TdkGenesysPSU


def register_instruments() -> None:
    register("psu", "tdk-genesys", lambda transport, config: TdkGenesysPSU(transport, config))
    register("psu", "generic", lambda transport, config: GenericPSU(transport, config))
