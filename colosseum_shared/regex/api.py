from __future__ import annotations

import re
from collections.abc import Sequence

from colosseum.context import require_context
from colosseum.decorators import (
    MeasurementSource,
    VerificationResult,
    missing_measurement_result,
    verification,
)


@verification(sources=[MeasurementSource(domain="shared", command="ssh.measure_stdout")])
def verify_match(
    *,
    key: str,
    pattern: str,
    optional: bool = False,
    sources: Sequence[MeasurementSource] | None = None,
) -> VerificationResult:
    """Verify a regex matches text from a prior measurement.

    :param key: Measurement key shared with the source measurement.
    :type key: str
    :param pattern: Regular expression searched in the measured text.
    :type pattern: str
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional
    :param sources: Override default ``ssh.measure_stdout`` source list.
    :type sources: Sequence[MeasurementSource] | None, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    source_list = list(sources or [MeasurementSource("shared", "ssh.measure_stdout")])
    actual = None
    for source in source_list:
        row = require_context().db.get_measurement(source.domain, source.command, key, row_index=0)
        if row is not None and row.value is not None:
            actual = str(row.value)
            break
    if actual is None:
        return missing_measurement_result(key=key, optional=optional)
    if re.search(pattern, actual):
        return VerificationResult(status="PASS", message="", optional=optional, actual=actual)
    return VerificationResult(
        status="FAIL",
        message=f"pattern {pattern!r} not found in {actual!r}",
        optional=optional,
        actual=actual,
    )
