from __future__ import annotations

from colosseum_equipment.instruments.registry import register

from .generic import GenericASG


def register_instruments() -> None:
    register("asg", "generic", lambda transport, config: GenericASG(transport, config))
