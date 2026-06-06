from __future__ import annotations

from colosseum_equipment.instruments.registry import register

from .generic import GenericSdr


def register_instruments() -> None:
    register("sdr", "generic", lambda transport, config: GenericSdr(transport, config))
