"""Persist decorated verification results and feed the run result aggregator."""

from __future__ import annotations

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
    finish_dry_run_missing_key,
    invoke_dry_run_substitute,
    publish_description_parameter,
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
    if number != number or number in (float("inf"), float("-inf")):  # noqa: PLR0124
        return None
    return number


def _parse_signed_band(text: str) -> tuple[str, float] | None:
    """Return ``(\"+\", N)`` or ``(\"-\", N)`` for signed numeric strings like ``\"+10\"``."""
    if len(text) < 2 or text[0] not in "+-":
        return None
    try:
        magnitude = float(text[1:])
    except ValueError:
        return None
    if magnitude != magnitude or magnitude in (float("inf"), float("-inf")):  # noqa: PLR0124
        return None
    if magnitude < 0:
        return None
    return text[0], magnitude


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
        passed = actual == expected
        return _pass_or_fail(
            passed=passed,
            actual=actual,
            optional=optional,
            fail_message=f"expected {expected}, got {actual}",
        )

    if isinstance(tolerance, (int, float)):
        actual_n = _as_finite_number(actual)
        expected_n = _as_finite_number(expected)
        if actual_n is None or expected_n is None:
            return _error_result(
                "non-numeric actual/expected for numeric tolerance",
                actual=actual,
                optional=optional,
            )
        band = abs(float(tolerance))
        passed = abs(actual_n - expected_n) <= band
        return _pass_or_fail(
            passed=passed,
            actual=actual,
            optional=optional,
            fail_message=f"expected {expected} +/- {band}, got {actual}",
        )

    if isinstance(tolerance, str):
        text = tolerance.strip()
        signed = _parse_signed_band(text)
        if signed is not None:
            actual_n = _as_finite_number(actual)
            expected_n = _as_finite_number(expected)
            if actual_n is None or expected_n is None:
                return _error_result(
                    "non-numeric actual/expected for numeric tolerance",
                    actual=actual,
                    optional=optional,
                )
            side, magnitude = signed
            if side == "+":
                passed = expected_n <= actual_n <= expected_n + magnitude
                label = f"+{magnitude}"
            else:
                passed = expected_n - magnitude <= actual_n <= expected_n
                label = f"-{magnitude}"
            return _pass_or_fail(
                passed=passed,
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

        actual_n = _as_finite_number(actual)
        expected_n = _as_finite_number(expected)
        if actual_n is None or expected_n is None:
            return _error_result(
                "non-numeric actual/expected for numeric tolerance",
                actual=actual,
                optional=optional,
            )
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


def _verification_fields(kwargs: dict[str, Any]) -> tuple[Any, str | None, float | None]:
    if kwargs.get("compare_op") == "LOG":
        return None, "LOG", None
    if "expected_val" in kwargs:
        return kwargs["expected_val"], "GELE", kwargs.get("tolerance", 0.0)
    if "minimum" in kwargs:
        return kwargs["minimum"], "GE", None
    if "maximum" in kwargs:
        return kwargs["maximum"], "LE", None
    if "exact" in kwargs:
        return kwargs["exact"], "EQ", None
    if "expected" in kwargs:
        expected = kwargs["expected"]
        return expected, "EQ" if isinstance(expected, str) else None, None
    return None, None, None


def _clean_description(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_verification_result(raw_result: object, *, optional: bool) -> VerificationResult:
    if isinstance(raw_result, VerificationResult):
        return raw_result
    if isinstance(raw_result, bool):
        return VerificationResult(
            status="PASS" if raw_result else "FAIL",
            message="" if raw_result else "verification returned False",
            optional=optional,
        )
    return VerificationResult(status="PASS", message=str(raw_result), optional=optional)


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

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            ctx = ensure_runtime_context()
            if should_skip_verification(ctx):
                return None
            key, injected = resolve_auto_key(ctx, kwargs, family="verification")
            key_text = "" if not key else str(key)
            if capture_parameter_export(
                ctx, kind="verification", command=command, key=key_text, kwargs=kwargs,
            ):
                return None
            if finish_dry_run_missing_key(
                ctx,
                kind="verification",
                domain=domain,
                command=command,
                key=key_text,
                call_args=args,
                kwargs=kwargs,
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
                apply_parameters=not injected,
                pop_key=injected and not accepts_key,
                pop_description=not accepts_description,
                require_prior_measurement=True,
            ):
                return None
            if not key:
                description = _clean_description(kwargs.get("description"))
                try:
                    optional = coerce_bool(kwargs["optional"]) if "optional" in kwargs else False
                    message = f"`{command}` requires `key=`"
                except ParametersError as exc:
                    optional = False
                    message = str(exc)
                result = VerificationResult(
                    status="ERROR", message=message, optional=optional,
                )
                ctx.result_aggregator.record_verification(
                    result,
                    key="",
                    command=command,
                    domain=domain,
                    description=description or "",
                )
                ctx.db.insert_verification(
                    VerificationRow(
                        domain=domain,
                        command=command,
                        key="<missing>",
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
                    key="",
                    status=result.status,
                    optional=result.optional,
                    detail=f"message={result.message!r}",
                    call_args=args,
                    kwargs=kwargs,
                )
                return result

            call_kwargs = dict(kwargs)
            try:
                if not injected:
                    call_kwargs = apply_parameters_to_kwargs(
                        call_kwargs,
                        key=str(key),
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
                    key=str(key),
                    command=command,
                    domain=domain,
                    description=description or "",
                )
                expected, compare_op, tolerance = _verification_fields(call_kwargs)
                ctx.db.insert_verification(
                    VerificationRow(
                        domain=domain,
                        command=command,
                        key=key,
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
                    key=str(key),
                    status=result.status,
                    optional=result.optional,
                    detail=f"message={result.message!r}",
                    call_args=args,
                    kwargs=kwargs,
                )
                return result

            description = _clean_description(call_kwargs.get("description"))
            logged_kwargs = dict(call_kwargs)
            if not accepts_description:
                call_kwargs.pop("description", None)
            if injected and not accepts_key:
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
                    func(*args, **call_kwargs), optional=optional,
                )
            except Exception as exc:  # noqa: BLE001
                log_evidence_error(
                    ctx,
                    kind="verification",
                    domain=domain,
                    command=command,
                    key=str(key),
                    call_args=args,
                    kwargs=logged_kwargs,
                )
                result = VerificationResult(status="ERROR", message=str(exc), optional=optional)
            ctx.result_aggregator.record_verification(
                result,
                key=str(key),
                command=command,
                domain=domain,
                description=description or "",
            )
            expected, compare_op, tolerance = _verification_fields(call_kwargs)
            ctx.db.insert_verification(
                VerificationRow(
                    domain=domain,
                    command=command,
                    key=key,
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
                key=str(key),
                status=result.status,
                optional=result.optional,
                detail=(
                    f"expected={call_kwargs.get('expected_val')!r} "
                    f"message={result.message!r}"
                ),
                call_args=args,
                kwargs=logged_kwargs,
            )
            return result

        setattr(wrapper, COLOSSEUM_DECORATOR, "verification")
        bind_dry_run_policy(wrapper, dry_run)
        publish_description_parameter(wrapper, func)
        return wrapper

    if _func is None:
        return decorate
    return decorate(_func)
