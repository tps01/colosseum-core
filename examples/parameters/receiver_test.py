"""Example script that reads limit kwargs from a parameters file via key=.

Run once per limits file::

    colosseum run receiver_test.py --parameters limits_low.toml -g <config>
    colosseum run receiver_test.py --parameters limits_high.toml -g <config>

Or both entries from the suite::

    colosseum run-suite receiver_suite.toml -g <config>
"""

from __future__ import annotations

import colosseum as col
from colosseum.context import get_context
from colosseum.decorators import measurement, verification
from colosseum.decorators.verification import VerificationResult, missing_measurement_result


@measurement
def measure_level(*, key: str, value: float) -> float:
    return value


@verification
def verify_level(
    *,
    key: str,
    expected_val: float,
    tolerance: float = 0.0,
) -> VerificationResult:
    measured = get_context().db.get_measurement("core", "measure_level", key)
    if measured is None:
        return missing_measurement_result(key=key)
    actual = float(measured.value)
    low = expected_val - tolerance
    high = expected_val + tolerance
    if low <= actual <= high:
        return VerificationResult(status="PASS", actual=actual)
    return VerificationResult(
        status="FAIL",
        message=f"{actual} not in [{low}, {high}]",
        actual=actual,
    )


def main() -> None:
    # Simulated receiver reading; limits come from the parameters section for key=.
    measure_level(key="rx_level", value=0.0)
    verify_level(key="rx_level")


if __name__ == "__main__":
    main()
    col.endex()
