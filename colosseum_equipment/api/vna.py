from __future__ import annotations

from colosseum_equipment.connections import get_cached_instrument


def preset(*, vna_id: int) -> None:
    get_cached_instrument("vna", vna_id).preset()


def set_start_frequency(*, vna_id: int, frequency_hz: float) -> None:
    get_cached_instrument("vna", vna_id).set_start_frequency(frequency_hz)


def set_stop_frequency(*, vna_id: int, frequency_hz: float) -> None:
    get_cached_instrument("vna", vna_id).set_stop_frequency(frequency_hz)


def set_points(*, vna_id: int, count: int) -> None:
    get_cached_instrument("vna", vna_id).set_points(count)


def single_sweep(*, vna_id: int) -> None:
    get_cached_instrument("vna", vna_id).single_sweep()


def wait_complete(*, vna_id: int) -> None:
    get_cached_instrument("vna", vna_id).wait_complete()
