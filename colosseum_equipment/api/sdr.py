"""SDR APIs (``col.equipment.sdr``). UHD drivers require vendor documentation."""

from __future__ import annotations

from colosseum_equipment.connections import get_cached_instrument


def set_center_frequency(*, sdr_id: int, frequency_hz: float) -> None:
    get_cached_instrument("sdr", sdr_id).set_center_frequency(frequency_hz)


def set_sample_rate(*, sdr_id: int, sample_rate: float) -> None:
    get_cached_instrument("sdr", sdr_id).set_sample_rate(sample_rate)


def set_gain(*, sdr_id: int, gain_db: float) -> None:
    get_cached_instrument("sdr", sdr_id).set_gain(gain_db)


def capture_iq(*, sdr_id: int, path: str) -> None:
    get_cached_instrument("sdr", sdr_id).capture_iq(path)
