from __future__ import annotations

from colosseum_equipment.instruments.registry import register

from .generic import GenericOscope
from .tek_mdo4000 import TekMdo4000Oscope
from .tek_t3dso2000 import TekT3dso2000Oscope


def register_instruments() -> None:
    register(
        "oscope", "tektronix-mdo4000", lambda transport, config: TekMdo4000Oscope(transport, config)
    )
    register(
        "oscope",
        "tektronix-t3dso2000",
        lambda transport, config: TekT3dso2000Oscope(transport, config),
    )
    register("oscope", "generic", lambda transport, config: GenericOscope(transport, config))
