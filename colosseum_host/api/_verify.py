"""Verification helpers for host measurement APIs."""

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


def verify_minimum(
    *,
    domain: str,
    command: str,
    key: str,
    minimum: float,
    optional: bool = False,
    unit: str = "",
) -> VerificationResult:
    row = require_context().db.get_measurement(domain, command, key, row_index=0)
    if row is None or row.value is None:
        return missing_measurement_result(key=key, optional=optional)
    actual = float(str(row.value))
    if actual >= minimum:
        return VerificationResult(status="PASS", message="", optional=optional, actual=actual)
    unit_suffix = f" {unit}" if unit else ""
    return VerificationResult(
        status="FAIL",
        message=f"expected >= {minimum}{unit_suffix}, got {actual}",
        optional=optional,
        actual=actual,
    )


def minimum_verifier(
    command: str,
    *,
    name: str,
    unit: str = "",
    domain: str = "host",
) -> Callable[..., VerificationResult]:
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
        minimum: float,
        optional: bool = False,
    ) -> VerificationResult:
        return verify_minimum(
            domain=domain,
            command=source_command,
            key=key,
            minimum=minimum,
            optional=optional,
            unit=unit,
        )

    verify.__name__ = name
    verify.__qualname__ = name
    verify.__module__ = str(caller_module)
    verify.__doc__ = (
        f"Require a prior ``{source_command}`` measurement to be at least a minimum value.\n\n"
        f":param key: Measurement key shared with the prior ``{source_command}`` call.\n"
        ":type key: str\n"
        ":param minimum: Minimum allowed numeric value.\n"
        ":type minimum: float\n"
        ":param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.\n"
        ":type optional: bool, optional\n\n"
        ":returns: VerificationResult with PASS, FAIL, or ERROR status.\n"
        ":rtype: VerificationResult"
    )
    return cast(
        Callable[..., VerificationResult],
        verification(sources=[MeasurementSource(domain=domain, command=source_command)])(verify),
    )
