from __future__ import annotations

from colosseum.decorators import MeasurementSource, VerificationResult, measurement, verification

from colosseum_equipment.api._verify import verify_tolerance
from colosseum_equipment.connections import get_cached_instrument


def set_mode(*, eload_id: int, mode: str) -> None:
    get_cached_instrument("eload", eload_id).set_mode(mode)


def set_current(*, eload_id: int, current: float) -> None:
    get_cached_instrument("eload", eload_id).set_current(current)


def set_voltage(*, eload_id: int, voltage: float) -> None:
    get_cached_instrument("eload", eload_id).set_voltage(voltage)


def set_input(*, eload_id: int, enabled: bool) -> None:
    get_cached_instrument("eload", eload_id).set_input(enabled)


def preset(*, eload_id: int) -> None:
    get_cached_instrument("eload", eload_id).preset()


@measurement
def measure_voltage(*, eload_id: int, key: str) -> float:
    return get_cached_instrument("eload", eload_id).measure_voltage()


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
def measure_current(*, eload_id: int, key: str) -> float:
    return get_cached_instrument("eload", eload_id).measure_current()


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
