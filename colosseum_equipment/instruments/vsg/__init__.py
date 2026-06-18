from __future__ import annotations

from colosseum_equipment.instruments.registry import register

from .generic import GenericVSG
from .keysight_esg import KeysightESGVSG


def register_instruments() -> None:
    register("vsg", "keysight-esg", lambda transport, config: KeysightESGVSG(transport, config))
    register("vsg", "generic", lambda transport, config: GenericVSG(transport, config))
