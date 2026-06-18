from __future__ import annotations

from colosseum_equipment.instruments.registry import register

from .adaura_r3 import AdauraR3Attn
from .generic import GenericAttn


def register_instruments() -> None:
    register("attn", "adaura-r3", lambda transport, config: AdauraR3Attn(transport, config))
    register("attn", "generic", lambda transport, config: GenericAttn(transport, config))
