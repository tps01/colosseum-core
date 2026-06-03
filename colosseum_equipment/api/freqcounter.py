from __future__ import annotations

from colosseum.decorators import MeasurementSource, VerificationResult, measurement, verification

from colosseum_equipment.api._verify import verify_tolerance
from colosseum_equipment.connections import get_cached_instrument


def set_gate_time(*, freqcounter_id: int, seconds: float) -> None:
    get_cached_instrument("freqcounter", freqcounter_id).set_gate_time(seconds)


def preset(*, freqcounter_id: int) -> None:
    get_cached_instrument("freqcounter", freqcounter_id).preset()


@measurement
def measure_frequency(*, freqcounter_id: int, key: str) -> float:
    return get_cached_instrument("freqcounter", freqcounter_id).measure_frequency()


@verification(sources=[MeasurementSource(domain="equipment", command="measure_frequency")])
def verify_frequency(
    *,
    key: str,
    expected_val: float,
    tolerance: float = 1.0,
    optional: bool = False,
) -> VerificationResult:
    return verify_tolerance(
        domain="equipment",
        command="measure_frequency",
        key=key,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )


@measurement
def measure_period(*, freqcounter_id: int, key: str) -> float:
    return get_cached_instrument("freqcounter", freqcounter_id).measure_period()
