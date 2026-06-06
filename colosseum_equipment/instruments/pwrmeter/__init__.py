from __future__ import annotations

from colosseum_equipment.instruments.registry import register, register_aliases

from .generic import GenericPwrMeter
from .keysight_u2000 import KeysightU2000PwrMeter


def register_instruments() -> None:
    register_aliases(
        "pwrmeter",
        ("keysight-u2001a", "keysight-u2000a", "keysight-u2000"),
        lambda transport, config: KeysightU2000PwrMeter(transport, config),
    )
    register("pwrmeter", "generic", lambda transport, config: GenericPwrMeter(transport, config))
