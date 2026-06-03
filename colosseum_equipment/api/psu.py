from __future__ import annotations

from colosseum.decorators import MeasurementSource, VerificationResult, measurement, verification

from colosseum_equipment.api._verify import verify_tolerance
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
def measure_current(*, psu_id: int, key: str) -> float:
    return get_cached_instrument("psu", psu_id).measure_current()


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
def measure_output_state(*, psu_id: int, key: str) -> float:
    enabled = get_cached_instrument("psu", psu_id).measure_output_state()
    return 1.0 if enabled else 0.0


@verification(sources=[MeasurementSource(domain="equipment", command="measure_output_state")])
def verify_output_state(
    *,
    key: str,
    expected_val: float,
    tolerance: float = 0.0,
    optional: bool = False,
) -> VerificationResult:
    return verify_tolerance(
        domain="equipment",
        command="measure_output_state",
        key=key,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )
