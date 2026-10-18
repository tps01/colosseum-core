"""Plugin-free numeric/text evidence, including verification-only replay.

From the core repository root::

    colosseum run examples/evidence_replay.py
    colosseum run examples/evidence_replay.py -u outputs/<completed-run>-pass
    colosseum run examples/evidence_replay.py --no-artifacts

Both measurements are skipped in verification-only mode; the imported rows
support the same two PASS results. No hardware, plugin or config is required.
"""

from __future__ import annotations

import re
from pathlib import Path

import colosseum as col
from colosseum.context import get_context
from colosseum.decorators import (
    VerificationResult,
    measurement,
    missing_measurement_result,
    verification,
)

__colosseum_domain__ = "example"


@measurement
def measure_reference(*, key: str, value: object) -> object:
    """Stand in for a captured device value; return it unchanged."""
    _ = key
    return value


@verification
def verify_voltage(*, key: str, expected_val: float, tolerance: float) -> VerificationResult:
    """Compare recorded voltage without acquiring it again."""
    row = get_context().db.get_measurement("example", "measure_reference", key)
    if row is None:
        return missing_measurement_result(key=key, optional=False)
    actual = float(row.value)
    passed = abs(actual - expected_val) <= tolerance
    return VerificationResult(status="PASS" if passed else "FAIL", actual=actual)


@verification
def verify_version(*, key: str, pattern: str) -> VerificationResult:
    """Match recorded text without consulting a live device."""
    row = get_context().db.get_measurement("example", "measure_reference", key)
    if row is None:
        return missing_measurement_result(key=key, optional=False)
    passed = re.fullmatch(pattern, str(row.value)) is not None
    return VerificationResult(status="PASS" if passed else "FAIL", actual=row.value)


def main() -> None:
    measure_reference(key="rail", value=3.31)
    measure_reference(key="version", value="v1.2.3")
    verify_voltage(key="rail", expected_val=3.3, tolerance=0.05)
    verify_version(key="version", pattern=r"v\d+\.\d+\.\d+")


if __name__ == "__main__":
    col.config.load_config(str(Path(__file__).with_name("config.empty.toml")))
    main()
    col.endex()
