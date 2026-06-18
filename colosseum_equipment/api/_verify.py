"""Shared verification helpers for equipment measurement APIs."""

from __future__ import annotations

import inspect
from typing import Callable, cast

from colosseum.context import require_context
from colosseum.decorators import (
    MeasurementSource,
    VerificationResult,
    missing_measurement_result,
    verification,
)
from colosseum.decorators._common import command_id_for_module

from colosseum_equipment.api._docstrings import tolerance_verify_doc


def verify_tolerance(
    *,
    domain: str,
    command: str,
    key: str,
    expected_val: float,
    tolerance: float,
    optional: bool = False,
    unit: str = "",
) -> VerificationResult:
    row = require_context().db.get_measurement(domain, command, key, row_index=0)
    if row is None or row.value is None:
        return missing_measurement_result(key=key, optional=optional)
    actual = float(str(row.value))
    if abs(actual - expected_val) <= tolerance:
        return VerificationResult(status="PASS", message="", optional=optional, actual=actual)
    unit_suffix = f" {unit}" if unit else ""
    return VerificationResult(
        status="FAIL",
        message=f"expected {expected_val} +/- {tolerance}{unit_suffix}, got {actual}",
        optional=optional,
        actual=actual,
    )


def tolerance_verifier(
    command: str,
    *,
    name: str,
    default_tolerance: float = 0.1,
    unit: str = "",
    domain: str = "equipment",
) -> Callable[..., VerificationResult]:
    """Build a @verification function that compares a prior measurement with tolerance."""
    frame = inspect.currentframe()
    caller_frame = frame.f_back if frame is not None else None
    caller_module = (
        caller_frame.f_globals.get("__name__", __name__) if caller_frame is not None else __name__
    )
    source_command = (
        command if "." in command else command_id_for_module(str(caller_module), command)
    )

    def verify(
        *,
        key: str,
        expected_val: float,
        tolerance: float = default_tolerance,
        optional: bool = False,
    ) -> VerificationResult:
        return verify_tolerance(
            domain=domain,
            command=source_command,
            key=key,
            expected_val=expected_val,
            tolerance=tolerance,
            optional=optional,
            unit=unit,
        )

    verify.__name__ = name
    verify.__qualname__ = name
    verify.__module__ = str(caller_module)
    verify.__doc__ = tolerance_verify_doc(source_command, unit=unit)
    return cast(
        Callable[..., VerificationResult],
        verification(sources=[MeasurementSource(domain=domain, command=source_command)])(verify),
    )
