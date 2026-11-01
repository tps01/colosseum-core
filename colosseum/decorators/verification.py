"""Persist decorated verification results and feed the run result aggregator."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import wraps
from inspect import signature
from typing import TYPE_CHECKING, Any, TypeVar, overload

from colosseum.config.parameters import (
    ParametersError,
    apply_parameters_to_kwargs,
    coerce_bool,
    coerce_optional_kwarg,
)
from colosseum.database import VerificationRow
from colosseum.units import coerce_units

from ._common import (
    bind_dry_run_policy,
    capture_parameter_export,
    ensure_runtime_context,
    finish_dry_run_log,
    invoke_dry_run_substitute,
    publish_description_parameter,
    publish_optional_parameter,
    resolve_auto_key,
    resolve_command,
    resolve_domain,
    should_skip_verification,
)
from ._kernel import log_evidence, log_evidence_error
from ._typing import ParamSpec
from .command import COLOSSEUM_DECORATOR

if TYPE_CHECKING:
    from collections.abc import Callable

P = ParamSpec("P")
R = TypeVar("R")


@dataclass
class VerificationResult:
    status: str
    message: str = ""
    optional: bool = False
    actual: Any = None

    def __post_init__(self) -> None:
        from colosseum.decorators._common import normalize_outcome_status

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
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            raise TypeError(f"expected finite numeric limit, got {value!r}")
        return number
    if isinstance(value, str):
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
        status="FAIL", message=fail_message, optional=optional, actual=actual,
    )


def _error_result(message: str, *, actual: object, optional: bool) -> VerificationResult:
    return VerificationResult(
        status="ERROR", message=message, optional=optional, actual=actual,
    )


def _require_numbers(
    actual: object, expected: object, *, optional: bool,
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
    if isinstance(tolerance, bool):
        return _error_result(
            f"unsupported tolerance {tolerance!r}", actual=actual, optional=optional,
        )

    if tolerance is None:
        return _pass_or_fail(
            passed=actual == expected,
            actual=actual,
            optional=optional,
            fail_message=f"expected {expected}, got {actual}",
        )

    if isinstance(tolerance, (int, float)):
        numbers = _require_numbers(actual, expected, optional=optional)
        if isinstance(numbers, VerificationResult):
            return numbers
        actual_n, expected_n = numbers
        band = abs(float(tolerance))
        return _pass_or_fail(
            passed=abs(actual_n - expected_n) <= band,
            actual=actual,
            optional=optional,
            fail_message=f"expected {expected} +/- {band}, got {actual}",
        )

    if isinstance(tolerance, str):
        text = tolerance.strip()
        signed = parse_signed_band(text)
        if signed is not None:
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

        op = _OPERATOR_ALIASES.get(text) or _OPERATOR_ALIASES.get(text.upper())
        if op is None:
            return _error_result(
                f"unknown tolerance {tolerance!r}", actual=actual, optional=optional,
            )

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

    return _error_result(
        f"unsupported tolerance {tolerance!r}", actual=actual, optional=optional,
    )


def _has_required_unit_command_error() -> bool:
    from colosseum.context import get_context

    try:
        records = get_context().result_aggregator._records  # noqa: SLF001
    except RuntimeError:
        return False
    for row in records:
        if (
            row["kind"] == "command"
            and not row["optional"]
            and row["status"] == "ERROR"
            and row.get("cause", "unit") == "unit"
        ):
            return True
    return False


def missing_measurement_result(*, key: str, optional: bool = False) -> VerificationResult:
    """Return ERROR (or BLOCKED) when a verification needs a key or measurement.

    Authors who require a key or prior measurement opt in from the body, for
    example ``if not key: return missing_measurement_result(key=key)`` or when
    ``get_measurement`` returns ``None``.
    """
    if not optional and _has_required_unit_command_error():
        return VerificationResult(
            status="BLOCKED",
            message=f"no measurement for key={key}",
            optional=optional,
        )
    return VerificationResult(
        status="ERROR",
        message=f"no measurement for key={key}",
        optional=optional,
    )


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


def _clean_description(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_verification_result(
    raw_result: object,
    *,
    optional: bool,
    kwargs: dict[str, Any],
) -> VerificationResult:
    if isinstance(raw_result, VerificationResult):
        return raw_result
    if isinstance(raw_result, bool):
        return VerificationResult(
            status="PASS" if raw_result else "FAIL",
            message="" if raw_result else "verification returned False",
            optional=optional,
        )
    limit = _auto_limit_args(kwargs)
    if limit is not None:
        expected, tolerance = limit
        return apply_tolerance(raw_result, expected, tolerance, optional=optional)
    return VerificationResult(
        status="PASS", message=str(raw_result), optional=optional, actual=raw_result,
    )


@overload
def verification(func: Callable[P, R], /) -> Callable[P, R]: ...


@overload
def verification(
    func: None = None, /, *, dry_run: object = "log",
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def verification(
    _func: Callable[..., Any] | None = None, *, dry_run: object = "log",
) -> object:
    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        domain = resolve_domain(func)
        command = resolve_command(func)
        parameters = signature(func).parameters
        accepts_description = "description" in parameters
        accepts_key = "key" in parameters
        accepts_optional = "optional" in parameters

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            ctx = ensure_runtime_context()
            if should_skip_verification(ctx):
                return None
            key, injected = resolve_auto_key(
                ctx, kwargs, family="verification", command=command,
            )
            key_text = "" if not key else str(key)
            if capture_parameter_export(
                ctx, kind="verification", command=command, key=key_text, kwargs=kwargs,
            ):
                return None
            if finish_dry_run_log(
                ctx,
                kind="verification",
                domain=domain,
                command=command,
                key=key_text,
                optional=False,
                policy=dry_run,
                func=func,
                call_args=args,
                kwargs=kwargs,
                description=_clean_description(kwargs.get("description")) or "",
                injected=injected,
                apply_parameters=bool(key) and not injected,
                pop_key=not accepts_key,
                pop_optional=not accepts_optional,
                pop_description=not accepts_description,
                require_prior_measurement=False,
            ):
                return None

            call_kwargs = dict(kwargs)
            try:
                if key and not injected:
                    call_kwargs = apply_parameters_to_kwargs(
                        call_kwargs,
                        key=key_text,
                        parameters=ctx.parameters_map,
                    )
                optional = coerce_optional_kwarg(call_kwargs)
            except ParametersError as exc:
                description = _clean_description(call_kwargs.get("description"))
                optional = False
                if "optional" in kwargs:
                    try:
                        optional = coerce_bool(kwargs["optional"])
                    except ParametersError:
                        optional = False
                result = VerificationResult(
                    status="ERROR", message=str(exc), optional=optional,
                )
                ctx.result_aggregator.record_verification(
                    result,
                    key=key_text,
                    command=command,
                    domain=domain,
                    description=description or "",
                )
                expected, compare_op, tolerance = verification_limit_fields(call_kwargs)
                ctx.db.insert_verification(
                    VerificationRow(
                        domain=domain,
                        command=command,
                        key=key_text,
                        expected=expected,
                        actual=None,
                        tolerance=tolerance,
                        compare_op=compare_op,
                        status=result.status,
                        optional=result.optional,
                        message=result.message,
                        description=description,
                    ),
                )
                log_evidence(
                    ctx,
                    kind="verification",
                    domain=domain,
                    command=command,
                    key=key_text,
                    status=result.status,
                    optional=result.optional,
                    detail=f"message={result.message!r}",
                    call_args=args,
                    kwargs=kwargs,
                )
                return result

            description = _clean_description(call_kwargs.get("description"))
            logged_kwargs = dict(call_kwargs)
            if not accepts_optional:
                call_kwargs.pop("optional", None)
            if not accepts_description:
                call_kwargs.pop("description", None)
            if not accepts_key:
                call_kwargs.pop("key", None)
            handled, value = invoke_dry_run_substitute(
                ctx,
                kind="verification",
                domain=domain,
                command=command,
                key=key_text,
                optional=optional,
                policy=dry_run,
                call_args=args,
                call_kwargs=call_kwargs,
                logged_kwargs=logged_kwargs,
                description=description or "",
            )
            if handled:
                return value

            try:
                call_kwargs = coerce_units(call_kwargs)
                result = _coerce_verification_result(
                    func(*args, **call_kwargs),
                    optional=optional,
                    kwargs=call_kwargs,
                )
            except Exception as exc:  # noqa: BLE001
                log_evidence_error(
                    ctx,
                    kind="verification",
                    domain=domain,
                    command=command,
                    key=key_text,
                    call_args=args,
                    kwargs=logged_kwargs,
                )
                result = VerificationResult(status="ERROR", message=str(exc), optional=optional)
            ctx.result_aggregator.record_verification(
                result,
                key=key_text,
                command=command,
                domain=domain,
                description=description or "",
            )
            expected, compare_op, tolerance = verification_limit_fields(call_kwargs)
            ctx.db.insert_verification(
                VerificationRow(
                    domain=domain,
                    command=command,
                    key=key_text,
                    expected=expected,
                    actual=result.actual,
                    tolerance=tolerance,
                    compare_op=compare_op,
                    status=result.status,
                    optional=result.optional,
                    message=result.message,
                    description=description,
                ),
            )
            log_evidence(
                ctx,
                kind="verification",
                domain=domain,
                command=command,
                key=key_text,
                status=result.status,
                optional=result.optional,
                detail=(
                    f"expected={_reference_expected(call_kwargs)!r} "
                    f"message={result.message!r}"
                ),
                call_args=args,
                kwargs=logged_kwargs,
            )
            return result

        setattr(wrapper, COLOSSEUM_DECORATOR, "verification")
        bind_dry_run_policy(wrapper, dry_run)
        publish_optional_parameter(wrapper, func)
        publish_description_parameter(wrapper, func)
        return wrapper

    if _func is None:
        return decorate
    return decorate(_func)
