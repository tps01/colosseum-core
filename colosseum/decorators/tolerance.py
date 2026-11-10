"""Tolerance DSL: compare a value to an expected reference and map limit kwargs to evidence."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ._common import normalize_outcome_status

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class VerificationResult:
    status: str
    message: str = ""
    optional: bool = False
    actual: Any = None

    def __post_init__(self) -> None:
        self.status = normalize_outcome_status(self.status)


_OPERATOR_ALIASES: dict[str, str] = {
    ">=": "GE",
    "GE": "GE",
    "<=": "LE",
    "LE": "LE",
    ">": "GT",
    "GT": "GT",
    "+": "GT",
    "<": "LT",
    "LT": "LT",
    "-": "LT",
    "==": "EQ",
    "=": "EQ",
    "EQ": "EQ",
    "!=": "NE",
    "<>": "NE",
    "NE": "NE",
}

_OP_SYMBOLS: dict[str, str] = {
    "GE": ">=",
    "LE": "<=",
    "GT": ">",
    "LT": "<",
    "EQ": "==",
    "NE": "!=",
}


def _as_finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _limit_number(value: object) -> float:
    """Coerce a limit value to float. Strings such as ``\"3.3\"`` are accepted."""
    if isinstance(value, bool):
        raise TypeError(f"expected numeric limit, got {type(value)!r}")
    if isinstance(value, (int, float, str)):
        number = float(value)
        if not math.isfinite(number):
            raise TypeError(f"expected finite numeric limit, got {value!r}")
        return number
    raise TypeError(f"expected numeric limit, got {type(value)!r}")


def parse_signed_band(text: str) -> tuple[str, float] | None:
    """Return ``(\"+\", N)`` or ``(\"-\", N)`` for signed numeric strings like ``\"+10\"``."""
    if len(text) < 2 or text[0] not in "+-":
        return None
    try:
        magnitude = float(text[1:])
    except ValueError:
        return None
    if not math.isfinite(magnitude) or magnitude < 0:
        return None
    return text[0], magnitude


def gele_limits(expected: object, tolerance: object) -> tuple[float, float]:
    """Expand a GELE expected/tolerance pair to inclusive ``(low, high)``.

    :param expected: Center / reference value for the band.
    :type expected: object
    :param tolerance: ± magnitude, signed one-sided string (``\"+10\"`` / ``\"-10\"``),
        or ``None`` for a zero-width band.
    :type tolerance: object
    :returns: Inclusive low and high limits.
    :rtype: tuple[float, float]
    """
    exp = _limit_number(expected)
    if isinstance(tolerance, str):
        signed = parse_signed_band(tolerance.strip())
        if signed is not None:
            side, magnitude = signed
            if side == "+":
                return exp, exp + magnitude
            return exp - magnitude, exp
        return gele_limits(exp, float(tolerance))
    if tolerance is None:
        return exp, exp
    band = abs(_limit_number(tolerance))
    return exp - band, exp + band


def _pass_or_fail(
    *,
    passed: bool,
    actual: object,
    optional: bool,
    fail_message: str,
) -> VerificationResult:
    if passed:
        return VerificationResult(status="PASS", message="", optional=optional, actual=actual)
    return VerificationResult(
        status="FAIL",
        message=fail_message,
        optional=optional,
        actual=actual,
    )


def _error_result(message: str, *, actual: object, optional: bool) -> VerificationResult:
    return VerificationResult(
        status="ERROR",
        message=message,
        optional=optional,
        actual=actual,
    )


def _require_numbers(
    actual: object,
    expected: object,
    *,
    optional: bool,
) -> tuple[float, float] | VerificationResult:
    actual_n = _as_finite_number(actual)
    expected_n = _as_finite_number(expected)
    if actual_n is None or expected_n is None:
        return _error_result(
            "non-numeric actual/expected for numeric tolerance",
            actual=actual,
            optional=optional,
        )
    return actual_n, expected_n


def _tol_none(
    actual: object,
    expected: object,
    tolerance: object,
    *,
    optional: bool,
) -> VerificationResult:
    del tolerance
    return _pass_or_fail(
        passed=actual == expected,
        actual=actual,
        optional=optional,
        fail_message=f"expected {expected}, got {actual}",
    )


def _tol_numeric(
    actual: object,
    expected: object,
    tolerance: object,
    *,
    optional: bool,
) -> VerificationResult:
    numbers = _require_numbers(actual, expected, optional=optional)
    if isinstance(numbers, VerificationResult):
        return numbers
    actual_n, expected_n = numbers
    band = abs(float(tolerance))  # type: ignore[arg-type]
    return _pass_or_fail(
        passed=abs(actual_n - expected_n) <= band,
        actual=actual,
        optional=optional,
        fail_message=f"expected {expected} +/- {band}, got {actual}",
    )


def _tol_str_signed(
    actual: object,
    expected: object,
    text: str,
    signed: tuple[str, float],
    *,
    optional: bool,
) -> VerificationResult:
    numbers = _require_numbers(actual, expected, optional=optional)
    if isinstance(numbers, VerificationResult):
        return numbers
    actual_n, expected_n = numbers
    low, high = gele_limits(expected_n, text)
    side, magnitude = signed
    label = f"{side}{magnitude}"
    return _pass_or_fail(
        passed=low <= actual_n <= high,
        actual=actual,
        optional=optional,
        fail_message=f"expected {expected} {label}, got {actual}",
    )


def _tol_str_operator(
    actual: object,
    expected: object,
    op: str,
    *,
    optional: bool,
) -> VerificationResult:
    symbol = _OP_SYMBOLS[op]
    if op in {"EQ", "NE"}:
        passed = (actual == expected) if op == "EQ" else (actual != expected)
        return _pass_or_fail(
            passed=passed,
            actual=actual,
            optional=optional,
            fail_message=f"expected {symbol} {expected}, got {actual}",
        )
    numbers = _require_numbers(actual, expected, optional=optional)
    if isinstance(numbers, VerificationResult):
        return numbers
    actual_n, expected_n = numbers
    comparisons = {
        "GE": actual_n >= expected_n,
        "LE": actual_n <= expected_n,
        "GT": actual_n > expected_n,
        "LT": actual_n < expected_n,
    }
    return _pass_or_fail(
        passed=comparisons[op],
        actual=actual,
        optional=optional,
        fail_message=f"expected {symbol} {expected}, got {actual}",
    )


def _tol_str(
    actual: object,
    expected: object,
    tolerance: object,
    *,
    optional: bool,
) -> VerificationResult:
    text = str(tolerance).strip()
    signed = parse_signed_band(text)
    if signed is not None:
        return _tol_str_signed(actual, expected, text, signed, optional=optional)
    op = _OPERATOR_ALIASES.get(text) or _OPERATOR_ALIASES.get(text.upper())
    if op is None:
        return _error_result(
            f"unknown tolerance {tolerance!r}",
            actual=actual,
            optional=optional,
        )
    return _tol_str_operator(actual, expected, op, optional=optional)


def _tol_unsupported(
    actual: object,
    expected: object,
    tolerance: object,
    *,
    optional: bool,
) -> VerificationResult:
    del expected
    return _error_result(
        f"unsupported tolerance {tolerance!r}",
        actual=actual,
        optional=optional,
    )


_TOLERANCE_HANDLERS: tuple[
    tuple[Callable[[object], bool], Callable[..., VerificationResult]],
    ...,
] = (
    (lambda tolerance: tolerance is None, _tol_none),
    (lambda tolerance: isinstance(tolerance, bool), _tol_unsupported),
    (lambda tolerance: isinstance(tolerance, (int, float)), _tol_numeric),
    (lambda tolerance: isinstance(tolerance, str), _tol_str),
)


def apply_tolerance(
    actual: object,
    expected: object,
    tolerance: object = None,
    *,
    optional: bool = False,
) -> VerificationResult:
    """Compare ``actual`` to ``expected`` using an overloaded ``tolerance``.

    :param actual: Measured or computed value under test.
    :type actual: object
    :param expected: Reference value for the comparison.
    :type expected: object
    :param tolerance: Numeric ± band, signed one-sided band string (``\"+10\"`` /
        ``\"-10\"``), comparison operator string, or ``None`` for exact match.
    :type tolerance: object, optional
    :param optional: Propagated onto the returned :class:`VerificationResult`.
    :type optional: bool, optional
    :returns: PASS/FAIL/ERROR result with ``actual`` set.
    :rtype: VerificationResult
    """
    for matches, handler in _TOLERANCE_HANDLERS:
        if matches(tolerance):
            return handler(actual, expected, tolerance, optional=optional)
    return _tol_unsupported(actual, expected, tolerance, optional=optional)


def _tolerance_evidence(tolerance: object) -> tuple[str, float | str | None]:
    """Map a ``tolerance`` value to ``(compare_op, stored_tolerance)`` for evidence."""
    if tolerance is None:
        return "EQ", None
    if isinstance(tolerance, bool):
        return "GELE", None
    if isinstance(tolerance, (int, float)):
        return "GELE", abs(float(tolerance))
    if isinstance(tolerance, str):
        text = tolerance.strip()
        if parse_signed_band(text) is not None:
            return "GELE", text
        op = _OPERATOR_ALIASES.get(text) or _OPERATOR_ALIASES.get(text.upper())
        if op is not None:
            return op, None
    return "GELE", None


def _reference_expected(kwargs: dict[str, Any]) -> object | None:
    if "expected_val" in kwargs:
        return kwargs["expected_val"]  # type: ignore[no-any-return]
    if "expected_result" in kwargs:
        return kwargs["expected_result"]  # type: ignore[no-any-return]
    return None


def verification_limit_fields(
    kwargs: dict[str, Any],
) -> tuple[Any, str | None, float | str | None]:
    """Map verification kwargs to ``(expected, compare_op, tolerance)`` for evidence.

    :param kwargs: Call kwargs after parameter fill (may include limit fields).
    :type kwargs: dict[str, Any]
    :returns: Expected value, compare op, and stored tolerance for the DB row.
    :rtype: tuple[Any, str | None, float | str | None]
    """
    if kwargs.get("compare_op") == "LOG":
        return None, "LOG", None
    if "expected_val" in kwargs or "expected_result" in kwargs:
        expected = _reference_expected(kwargs)
        if "tolerance" not in kwargs:
            return expected, "EQ", None
        compare_op, stored = _tolerance_evidence(kwargs["tolerance"])
        return expected, compare_op, stored
    if "minimum" in kwargs:
        return kwargs["minimum"], "GE", None
    if "maximum" in kwargs:
        return kwargs["maximum"], "LE", None
    if "exact" in kwargs:
        return kwargs["exact"], "EQ", None
    if "expected" in kwargs:
        value = kwargs["expected"]
        return value, "EQ" if isinstance(value, str) else None, None
    return None, None, None


def _auto_limit_args(kwargs: dict[str, Any]) -> tuple[object, object] | None:
    """Return ``(expected, tolerance)`` for :func:`apply_tolerance`, or ``None``."""
    expected, compare_op, stored = verification_limit_fields(kwargs)
    if compare_op == "LOG" or (expected is None and compare_op is None):
        return None
    if compare_op == "GELE":
        return expected, 0.0 if stored is None else stored
    if compare_op in _OP_SYMBOLS:
        # EQ from omitted tolerance uses None so messages stay "expected X, got Y".
        if compare_op == "EQ" and stored is None and "tolerance" not in kwargs:
            return expected, None
        return expected, compare_op
    return expected, None
