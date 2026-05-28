from __future__ import annotations

from colosseum.decorators import measurement

from colosseum_equipment.connections import get_cached_instrument


def set_voltage(*, psu_id: int, voltage: float) -> None:
    get_cached_instrument("psu", psu_id).set_voltage(voltage)


def set_current_limit(*, psu_id: int, current: float) -> None:
    get_cached_instrument("psu", psu_id).set_current_limit(current)


def set_output(*, psu_id: int, enabled: bool) -> None:
    get_cached_instrument("psu", psu_id).set_output(enabled)


@measurement
def measure_voltage(*, psu_id: int, key: str) -> float:
    return get_cached_instrument("psu", psu_id).measure_voltage()
