from __future__ import annotations

from colosseum.decorators import MeasurementSource, VerificationResult, measurement, verification

from colosseum_equipment.api._verify import verify_tolerance
from colosseum_equipment.connections import get_cached_instrument


def set_frequency(*, pwrmeter_id: int, frequency_hz: float) -> None:
    get_cached_instrument("pwrmeter", pwrmeter_id).set_frequency(frequency_hz)


def set_averaging_count(*, pwrmeter_id: int, count: int) -> None:
    get_cached_instrument("pwrmeter", pwrmeter_id).set_averaging_count(count)


def zero_sensor(*, pwrmeter_id: int) -> None:
    get_cached_instrument("pwrmeter", pwrmeter_id).zero_sensor()


def preset(*, pwrmeter_id: int) -> None:
    get_cached_instrument("pwrmeter", pwrmeter_id).preset()


@measurement
def measure_power(*, pwrmeter_id: int, key: str) -> float:
    return get_cached_instrument("pwrmeter", pwrmeter_id).measure_power()


@verification(sources=[MeasurementSource(domain="equipment", command="measure_power")])
def verify_power(
    *,
    key: str,
    expected_val: float,
    tolerance: float = 0.5,
    optional: bool = False,
) -> VerificationResult:
    return verify_tolerance(
        domain="equipment",
        command="measure_power",
        key=key,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )
