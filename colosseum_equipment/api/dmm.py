from __future__ import annotations

from colosseum.decorators import MeasurementSource, VerificationResult, measurement, verification
from colosseum.context import require_context

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
    row = require_context().db.get_measurement("equipment", "measure_voltage", key, row_index=0)
    if row is None or row.value is None:
        return VerificationResult(status="ERROR", message=f"no measurement for key={key}", optional=optional)
    actual = float(row.value)
    if abs(actual - expected_val) <= tolerance:
        return VerificationResult(status="PASS", message="", optional=optional)
    return VerificationResult(
        status="FAIL",
        message=f"expected {expected_val} +/- {tolerance}, got {actual}",
        optional=optional,
    )
