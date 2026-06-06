from __future__ import annotations

from colosseum_equipment.instruments.registry import register, register_aliases

from .generic import GenericRfSwitch
from .minicircuits_rc import MiniCircuitsRcSwitch


def register_instruments() -> None:
    register_aliases(
        "rfswitch",
        ("minicircuits-rc", "minicircuits-ztrc"),
        lambda transport, config: MiniCircuitsRcSwitch(transport, config),
    )
    register("rfswitch", "generic", lambda transport, config: GenericRfSwitch(transport, config))
