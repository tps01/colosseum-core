"""Small decorated API used to test the core runtime without plugins."""

from __future__ import annotations

from colosseum.context import get_context
from colosseum.decorators import VerificationResult, apply_tolerance, measurement, verification


@measurement
def measure_value(*, key: str, value: float) -> float:
    return value


@verification
def verify_value(
    *,
    key: str,
    expected_val: float,
    tolerance: float,
    optional: bool = False,
) -> VerificationResult:
    row = get_context().db.get_measurement("core", "measure_value", key)
    if row is None:
        return VerificationResult(status="ERROR", message=f"no measurement for key={key}")
    actual = float(row.value)
    return apply_tolerance(actual, expected_val, tolerance, optional=optional)
