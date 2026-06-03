"""Shared verification helpers for equipment measurement APIs."""

from __future__ import annotations

from colosseum.context import require_context
from colosseum.decorators import VerificationResult


def verify_tolerance(
    *,
    domain: str,
    command: str,
    key: str,
    expected_val: float,
    tolerance: float,
    optional: bool = False,
) -> VerificationResult:
    row = require_context().db.get_measurement(domain, command, key, row_index=0)
    if row is None or row.value is None:
        return VerificationResult(
            status="ERROR",
            message=f"no measurement for key={key}",
            optional=optional,
        )
    actual = float(row.value)
    if abs(actual - expected_val) <= tolerance:
        return VerificationResult(status="PASS", message="", optional=optional)
    return VerificationResult(
        status="FAIL",
        message=f"expected {expected_val} +/- {tolerance}, got {actual}",
        optional=optional,
    )
