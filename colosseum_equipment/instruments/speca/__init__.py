from __future__ import annotations

from colosseum_equipment.instruments.registry import register

from .generic import GenericSpecA
from .keysight_e4407b import KeysightE4407BSpecA


def register_instruments() -> None:
    register(
        "speca", "keysight-e4407b", lambda transport, config: KeysightE4407BSpecA(transport, config)
    )
    register("speca", "generic", lambda transport, config: GenericSpecA(transport, config))
