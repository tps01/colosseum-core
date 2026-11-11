"""Persist decorated verification results and feed the run result aggregator."""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from inspect import signature
from typing import TYPE_CHECKING, Any, ClassVar, Literal, TypeVar, overload

from colosseum.config.parameters import (
    ParametersError,
    apply_parameters_to_kwargs,
    coerce_optional_kwarg,
)
from colosseum.database import VerificationRow

from ._common import (
    bind_dry_run_policy,
    optional_from_caller,
    publish_description_parameter,
    publish_optional_parameter,
    publish_requirements_parameter,
    resolve_auto_key,
    resolve_command,
    resolve_domain,
    should_skip_verification,
)
from ._kernel import log_evidence, log_evidence_error
from ._pipeline import EarlyReturn, Identity, PreparedCall, run_decorated_call
from ._typing import ParamSpec
from .command import COLOSSEUM_DECORATOR
from .tolerance import (
    VerificationResult,
    _auto_limit_args,
    _reference_expected,
    apply_tolerance,
    verification_limit_fields,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from colosseum.context import RuntimeContext

P = ParamSpec("P")
R = TypeVar("R")


def _has_required_unit_command_error() -> bool:
    from colosseum.context import get_context

    try:
        return bool(get_context().result_aggregator.required_command_errors(cause="unit"))
    except RuntimeError:
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


def _clean_description(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _requirements_from_kwargs(kwargs: dict[str, Any]) -> list[str]:
    from colosseum.results.aggregation import coerce_requirements

    if "requirements" not in kwargs:
        return []
    return coerce_requirements(kwargs["requirements"])


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
        status="PASS",
        message=str(raw_result),
        optional=optional,
        actual=raw_result,
    )


def _safe_requirements(kwargs: dict[str, Any]) -> list[str]:
    try:
        return _requirements_from_kwargs(kwargs)
    except TypeError:
        return []


@dataclass
class _VerificationBinding:
    kind: ClassVar[Literal["verification"]] = "verification"
    domain: str
    command: str
    func: Callable[..., Any]
    dry_run: object
    accepts_description: bool
    accepts_requirements: bool
    accepts_key: bool
    accepts_optional: bool

    def should_skip(self, ctx: RuntimeContext) -> bool:
        return should_skip_verification(ctx)

    def resolve_identity(self, ctx: RuntimeContext, kwargs: dict[str, Any]) -> Identity:
        key, injected = resolve_auto_key(
            ctx,
            kwargs,
            family="verification",
            command=self.command,
        )
        key_text = "" if not key else str(key)
        return Identity(key=key, key_text=key_text, injected=injected)

    def dry_run_fields(
        self,
        identity: Identity,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "kind": "verification",
            "domain": self.domain,
            "command": self.command,
            "key": identity.key_text,
            "optional": False,
            "policy": self.dry_run,
            "func": self.func,
            "call_args": args,
            "kwargs": kwargs,
            "description": _clean_description(kwargs.get("description")) or "",
            "requirements": _safe_requirements(kwargs),
            "injected": identity.injected,
            "apply_parameters": bool(identity.key) and not identity.injected,
            "pop_key": not self.accepts_key,
            "pop_optional": not self.accepts_optional,
            "pop_description": not self.accepts_description,
            "pop_requirements": not self.accepts_requirements,
        }

    def prepare(
        self,
        ctx: RuntimeContext,
        identity: Identity,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> PreparedCall | EarlyReturn:
        call_kwargs = dict(kwargs)
        try:
            if identity.key and not identity.injected:
                call_kwargs = apply_parameters_to_kwargs(
                    call_kwargs,
                    key=identity.key_text,
                    parameters=ctx.parameters_map,
                )
            optional = coerce_optional_kwarg(call_kwargs)
        except ParametersError as exc:
            return EarlyReturn(
                self._persist_prepare_error(
                    ctx,
                    identity,
                    args=args,
                    limit_kwargs=call_kwargs,
                    message=str(exc),
                    optional=optional_from_caller(kwargs),
                    requirements=_safe_requirements(call_kwargs),
                    log_kwargs=kwargs,
                    include_requirements=True,
                ),
            )
        description = _clean_description(call_kwargs.get("description"))
        try:
            requirements = _requirements_from_kwargs(call_kwargs)
        except TypeError as exc:
            return EarlyReturn(
                self._persist_prepare_error(
                    ctx,
                    identity,
                    args=args,
                    limit_kwargs=call_kwargs,
                    message=str(exc),
                    optional=optional,
                    requirements=[],
                    log_kwargs=call_kwargs,
                    description=description,
                    include_requirements=False,
                ),
            )
        logged_kwargs = dict(call_kwargs)
        if not self.accepts_optional:
            call_kwargs.pop("optional", None)
        if not self.accepts_description:
            call_kwargs.pop("description", None)
        if not self.accepts_requirements:
            call_kwargs.pop("requirements", None)
        if not self.accepts_key:
            call_kwargs.pop("key", None)
        return PreparedCall(
            optional=optional,
            call_kwargs=call_kwargs,
            logged_kwargs=logged_kwargs,
            call_args=args,
            description=description or "",
            requirements=requirements,
        )

    def _persist_prepare_error(
        self,
        ctx: RuntimeContext,
        identity: Identity,
        *,
        args: tuple[Any, ...],
        limit_kwargs: dict[str, Any],
        message: str,
        optional: bool,
        requirements: list[str],
        log_kwargs: dict[str, Any],
        description: str | None = None,
        include_requirements: bool,
    ) -> VerificationResult:
        if description is None:
            description = _clean_description(limit_kwargs.get("description"))
        result = VerificationResult(status="ERROR", message=message, optional=optional)
        ctx.result_aggregator.record_verification(
            result,
            key=identity.key_text,
            command=self.command,
            domain=self.domain,
            description=description or "",
            requirements=requirements,
        )
        expected, compare_op, tolerance = verification_limit_fields(limit_kwargs)
        row_kwargs: dict[str, Any] = {
            "domain": self.domain,
            "command": self.command,
            "key": identity.key_text,
            "expected": expected,
            "actual": None,
            "tolerance": tolerance,
            "compare_op": compare_op,
            "status": result.status,
            "optional": result.optional,
            "message": result.message,
            "description": description,
        }
        if include_requirements:
            row_kwargs["requirements"] = requirements
        ctx.db.insert_verification(VerificationRow(**row_kwargs))
        log_evidence(
            ctx,
            kind="verification",
            domain=self.domain,
            command=self.command,
            key=identity.key_text,
            status=result.status,
            optional=result.optional,
            detail=f"message={result.message!r}",
            call_args=args,
            kwargs=log_kwargs,
        )
        return result

    def persist_success(
        self,
        ctx: RuntimeContext,
        identity: Identity,
        prepared: PreparedCall,
        value: object,
    ) -> object:
        result = _coerce_verification_result(
            value,
            optional=prepared.optional,
            kwargs=prepared.call_kwargs,
        )
        self._persist_outcome(ctx, identity, prepared, result)
        return result

    def persist_error(
        self,
        ctx: RuntimeContext,
        identity: Identity,
        prepared: PreparedCall,
        exc: Exception,
    ) -> object:
        log_evidence_error(
            ctx,
            kind="verification",
            domain=self.domain,
            command=self.command,
            key=identity.key_text,
            call_args=prepared.call_args,
            kwargs=prepared.logged_kwargs,
        )
        result = VerificationResult(
            status="ERROR",
            message=str(exc),
            optional=prepared.optional,
        )
        self._persist_outcome(ctx, identity, prepared, result)
        return result

    def _persist_outcome(
        self,
        ctx: RuntimeContext,
        identity: Identity,
        prepared: PreparedCall,
        result: VerificationResult,
    ) -> None:
        description = prepared.description or None
        ctx.result_aggregator.record_verification(
            result,
            key=identity.key_text,
            command=self.command,
            domain=self.domain,
            description=description or "",
            requirements=prepared.requirements,
        )
        expected, compare_op, tolerance = verification_limit_fields(prepared.call_kwargs)
        ctx.db.insert_verification(
            VerificationRow(
                domain=self.domain,
                command=self.command,
                key=identity.key_text,
                expected=expected,
                actual=result.actual,
                tolerance=tolerance,
                compare_op=compare_op,
                status=result.status,
                optional=result.optional,
                message=result.message,
                description=description,
                requirements=prepared.requirements,
            ),
        )
        log_evidence(
            ctx,
            kind="verification",
            domain=self.domain,
            command=self.command,
            key=identity.key_text,
            status=result.status,
            optional=result.optional,
            detail=(f"expected={_reference_expected(prepared.call_kwargs)!r} message={result.message!r}"),
            call_args=prepared.call_args,
            kwargs=prepared.logged_kwargs,
        )


@overload
def verification(func: Callable[P, R], /) -> Callable[P, R]: ...


@overload
def verification(
    func: None = None,
    /,
    *,
    dry_run: object = "log",
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def verification(
    _func: Callable[..., Any] | None = None,
    *,
    dry_run: object = "log",
) -> object:
    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        parameters = signature(func).parameters
        binding = _VerificationBinding(
            domain=resolve_domain(func),
            command=resolve_command(func),
            func=func,
            dry_run=dry_run,
            accepts_description="description" in parameters,
            accepts_requirements="requirements" in parameters,
            accepts_key="key" in parameters,
            accepts_optional="optional" in parameters,
        )

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            return run_decorated_call(binding, *args, **kwargs)

        setattr(wrapper, COLOSSEUM_DECORATOR, "verification")
        bind_dry_run_policy(wrapper, dry_run)
        publish_optional_parameter(wrapper, func)
        publish_description_parameter(wrapper, func)
        publish_requirements_parameter(wrapper, func)
        return wrapper

    if _func is None:
        return decorate
    return decorate(_func)
