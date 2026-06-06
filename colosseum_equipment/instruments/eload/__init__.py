from __future__ import annotations

from colosseum_equipment.instruments.registry import register, register_aliases

from .agilent_6050 import Agilent6050Eload
from .chroma_8600 import Chroma8600Eload
from .generic import GenericEload
from .itech_it8600 import ItechIT8600Eload


def register_instruments() -> None:
    register("eload", "itech-it8600", lambda transport, config: ItechIT8600Eload(transport, config))
    register_aliases(
        "eload",
        ("chroma-8600", "chroma-8601"),
        lambda transport, config: Chroma8600Eload(transport, config),
    )
    register("eload", "agilent-6050", lambda transport, config: Agilent6050Eload(transport, config))
    register("eload", "generic", lambda transport, config: GenericEload(transport, config))
