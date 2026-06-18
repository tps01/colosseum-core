"""Public API for ``col.myvendor`` (example extension)."""

from __future__ import annotations

from colosseum.decorators import MeasurementSource, VerificationResult, measurement, verification

_FIXTURE_COUNTS: dict[int, int] = {}


def _fixture_count(fixture_id: int) -> int:
    return _FIXTURE_COUNTS.setdefault(fixture_id, fixture_id * 10)


@measurement
def measure_widget_count(*, fixture_id: int, key: str) -> float:
    """Return a simulated widget count for the configured fixture."""
    return float(_fixture_count(fixture_id))


@verification(sources=[MeasurementSource(domain="myvendor", command="measure_widget_count")])
def verify_widget_count(
    *,
    key: str,
    expected_val: float,
    tolerance: float = 0.0,
    optional: bool = False,
) -> VerificationResult:
    from colosseum.context import require_context
    from colosseum.decorators import missing_measurement_result

    row = require_context().db.get_measurement("myvendor", "measure_widget_count", key, row_index=0)
    if row is None or row.value is None:
        return missing_measurement_result(key=key, optional=optional)
    actual = float(row.value)
    if abs(actual - expected_val) <= tolerance:
        return VerificationResult(status="PASS", message="", optional=optional)
    return VerificationResult(
        status="FAIL",
        message=f"expected {expected_val} +/- {tolerance}, got {actual}",
        optional=optional,
    )
