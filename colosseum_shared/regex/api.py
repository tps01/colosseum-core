from __future__ import annotations

import re
from typing import Optional, Sequence

from colosseum.decorators import MeasurementSource, VerificationResult, verification
from colosseum.context import require_context


@verification(sources=[MeasurementSource(domain="shared", command="measure_stdout")])
def verify_match(
    *,
    key: str,
    pattern: str,
    optional: bool = False,
    sources: Optional[Sequence[MeasurementSource]] = None,
) -> VerificationResult:
    source_list = list(sources or [MeasurementSource("shared", "measure_stdout")])
    actual = None
    for source in source_list:
        row = require_context().db.get_measurement(source.domain, source.command, key, row_index=0)
        if row is not None and row.value is not None:
            actual = str(row.value)
            break
    if actual is None:
        return VerificationResult(
            status="ERROR",
            message=f"no measurement for key={key}",
            optional=optional,
        )
    if re.search(pattern, actual):
        return VerificationResult(status="PASS", message="", optional=optional)
    return VerificationResult(
        status="FAIL",
        message=f"pattern {pattern!r} not found in {actual!r}",
        optional=optional,
    )
