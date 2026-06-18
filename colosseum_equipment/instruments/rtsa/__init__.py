from __future__ import annotations

from colosseum_equipment.instruments.registry import register

from .generic import GenericRtsa
from .tektronix_rsa5100b import TektronixRSA5100BRtsa


def register_instruments() -> None:
    register(
        "rtsa",
        "tektronix-rsa5100b",
        lambda transport, config: TektronixRSA5100BRtsa(transport, config),
    )
    register("rtsa", "generic", lambda transport, config: GenericRtsa(transport, config))
