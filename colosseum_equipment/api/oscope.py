from __future__ import annotations

from colosseum.decorators import MeasurementSource, VerificationResult, measurement, verification

from colosseum_equipment.api._verify import verify_tolerance
from colosseum_equipment.connections import get_cached_instrument


def preset(*, oscope_id: int) -> None:
    get_cached_instrument("oscope", oscope_id).preset()


def set_timebase_scale(*, oscope_id: int, seconds_per_div: float) -> None:
    get_cached_instrument("oscope", oscope_id).set_timebase_scale(seconds_per_div)


def single_acquire(*, oscope_id: int) -> None:
    get_cached_instrument("oscope", oscope_id).single_acquire()


@measurement
def measure_vpp(*, oscope_id: int, channel: int = 1, key: str) -> float:
    return get_cached_instrument("oscope", oscope_id).measure_vpp(channel)


@verification(sources=[MeasurementSource(domain="equipment", command="measure_vpp")])
def verify_vpp(
    *,
    key: str,
    expected_val: float,
    tolerance: float = 0.1,
    optional: bool = False,
) -> VerificationResult:
    return verify_tolerance(
        domain="equipment",
        command="measure_vpp",
        key=key,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )


def save_screenshot(*, oscope_id: int, path: str) -> None:
    get_cached_instrument("oscope", oscope_id).save_screenshot(path)
