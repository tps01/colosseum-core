from __future__ import annotations

from colosseum.decorators import measurement

from colosseum_equipment.connections import get_cached_instrument


def set_path(*, rfswitch_id: int, path: str) -> None:
    """Set routing path (model-specific string, e.g. ``A=1;B=0`` or ``SETP=0011``)."""
    get_cached_instrument("rfswitch", rfswitch_id).set_path(path)


def set_switch(*, rfswitch_id: int, switch: str, state: int) -> None:
    """Set one switch letter (Mini-Circuits ``SETA=1`` style)."""
    get_cached_instrument("rfswitch", rfswitch_id).set_switch(switch, state)


def preset(*, rfswitch_id: int) -> None:
    get_cached_instrument("rfswitch", rfswitch_id).preset()


@measurement
def measure_path(*, rfswitch_id: int, key: str) -> str:
    return get_cached_instrument("rfswitch", rfswitch_id).measure_path()
