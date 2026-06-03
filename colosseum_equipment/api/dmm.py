from __future__ import annotations

from colosseum.decorators import MeasurementSource, VerificationResult, measurement, verification

from colosseum_equipment.api._verify import verify_tolerance
from colosseum_equipment.connections import get_cached_instrument


@measurement
def measure_voltage(*, dmm_id: int, channel: int, key: str) -> float:
    instrument = get_cached_instrument("dmm", dmm_id)
    return instrument.measure_voltage(channel)


@verification(sources=[MeasurementSource(domain="equipment", command="measure_voltage")])
def verify_voltage(
    *,
    key: str,
    expected_val: float,
    tolerance: float = 0.1,
    optional: bool = False,
) -> VerificationResult:
    return verify_tolerance(
        domain="equipment",
        command="measure_voltage",
        key=key,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )


@measurement
def measure_current(*, dmm_id: int, channel: int, key: str) -> float:
    return get_cached_instrument("dmm", dmm_id).measure_current(channel)


@verification(sources=[MeasurementSource(domain="equipment", command="measure_current")])
def verify_current(
    *,
    key: str,
    expected_val: float,
    tolerance: float = 0.1,
    optional: bool = False,
) -> VerificationResult:
    return verify_tolerance(
        domain="equipment",
        command="measure_current",
        key=key,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )


@measurement
def measure_resistance(*, dmm_id: int, channel: int, key: str) -> float:
    return get_cached_instrument("dmm", dmm_id).measure_resistance(channel)


@verification(sources=[MeasurementSource(domain="equipment", command="measure_resistance")])
def verify_resistance(
    *,
    key: str,
    expected_val: float,
    tolerance: float = 0.1,
    optional: bool = False,
) -> VerificationResult:
    return verify_tolerance(
        domain="equipment",
        command="measure_resistance",
        key=key,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )
