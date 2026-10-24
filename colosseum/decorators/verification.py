"""Persist decorated verification results and feed the run result aggregator."""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from inspect import signature
from typing import TYPE_CHECKING, Any, TypeVar, overload

from colosseum.config.parameters import ParametersError, apply_parameters_to_kwargs
from colosseum.database import VerificationRow

from ._common import (
    ensure_runtime_context,
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
def verification(func: None = None, /) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def verification(_func: Callable[..., Any] | None = None) -> object:
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
            optional = bool(kwargs.get("optional", False))
            if not key:
                description = _clean_description(kwargs.get("description"))
                result = VerificationResult(
                    status="ERROR", message=f"`{command}` requires `key=`", optional=optional,
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
            if not injected:
                try:
                    call_kwargs = apply_parameters_to_kwargs(
                        call_kwargs,
                        key=str(key),
                        parameters=ctx.parameters_map,
                    )
                except ParametersError as exc:
                    description = _clean_description(kwargs.get("description"))
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

            try:
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
        publish_description_parameter(wrapper, func)
        return wrapper

    if _func is None:
        return decorate
    return decorate(_func)
