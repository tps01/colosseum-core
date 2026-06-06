from __future__ import annotations

from typing import Any

from colosseum_equipment.instruments.registry import build_registered
from colosseum_equipment.transports.base import Transport

from . import (
    asg,
    attn,
    dmm,
    eload,
    freqcounter,
    oscope,
    psu,
    pwrmeter,
    rfswitch,
    rtsa,
    sdr,
    speca,
    vna,
    vsg,
)

_REGISTRATION_MODULES = (
    dmm,
    psu,
    vsg,
    asg,
    speca,
    rtsa,
    attn,
    pwrmeter,
    rfswitch,
    oscope,
    eload,
    freqcounter,
    vna,
    sdr,
)


def _populate_registry() -> None:
    for module in _REGISTRATION_MODULES:
        module.register_instruments()


def build_instrument(
    kind: str, equipment_id: int, config: dict[str, Any], transport: Transport
) -> object:
    model = str(config.get("model", "generic")).lower()
    try:
        return build_registered(kind, model, transport, config)
    except RuntimeError as exc:
        if "Unsupported equipment model" in str(exc):
            raise RuntimeError(
                f"Unsupported equipment model `{model}` for {kind} id {equipment_id}"
            ) from exc
        raise


_populate_registry()
