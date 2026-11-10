"""Persist decorated command invocations and feed the run result aggregator."""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from inspect import signature
from typing import TYPE_CHECKING, Any, TypeVar, overload

from colosseum.config.parameters import (
    ParametersError,
    apply_parameters_to_kwargs,
    coerce_optional_kwarg,
)
from colosseum.database import CommandRow
from colosseum.exceptions import ProceduralFault

from ._common import (
    bind_dry_run_policy,
    optional_from_caller,
    publish_optional_parameter,
    resolve_command,
    resolve_domain,
    should_skip_command,
)
from ._kernel import log_evidence, log_evidence_error, record_error_event, short_repr
from ._pipeline import DecoratorSpec, EarlyReturn, Identity, PreparedCall, run_decorated_call
from ._typing import ParamSpec

if TYPE_CHECKING:
    from collections.abc import Callable

    from colosseum.context import RuntimeContext

COLOSSEUM_DECORATOR = "__colosseum_decorator__"

P = ParamSpec("P")
R = TypeVar("R")


@dataclass
class CommandResult:
    status: str
    message: str = ""
    optional: bool = False

    def __post_init__(self) -> None:
        from colosseum.decorators._common import normalize_outcome_status

        self.status = normalize_outcome_status(self.status)


def _command_cause(exc: BaseException) -> str:
    return "procedural" if isinstance(exc, ProceduralFault) else "unit"


@dataclass
class _CommandBinding:
    domain: str
    command_name: str
    func: Callable[..., Any]
    dry_run: object
    accepts_optional: bool
    accepts_key: bool

    def should_skip(self, ctx: RuntimeContext) -> bool:
        return should_skip_command(ctx)

    def resolve_identity(self, ctx: RuntimeContext, kwargs: dict[str, Any]) -> Identity:
        del ctx
        key_raw = kwargs.get("key")
        key = str(key_raw) if key_raw is not None and str(key_raw) != "" else ""
        return Identity(key=key, key_text=key)

    def dry_run_fields(
        self,
        identity: Identity,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "kind": "command",
            "domain": self.domain,
            "command": self.command_name,
            "key": identity.key_text,
            "optional": False,
            "policy": self.dry_run,
            "func": self.func,
            "call_args": args,
            "kwargs": kwargs,
            "apply_parameters": True,
            "pop_key": not self.accepts_key,
            "pop_optional": not self.accepts_optional,
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
            if identity.key_text:
                call_kwargs = apply_parameters_to_kwargs(
                    call_kwargs,
                    key=identity.key_text,
                    parameters=ctx.parameters_map,
                )
            optional = coerce_optional_kwarg(call_kwargs)
        except ParametersError as exc:
            return self._parameters_error(ctx, identity, args, kwargs, call_kwargs, exc)
        logged_kwargs = dict(call_kwargs)
        if not self.accepts_optional:
            call_kwargs.pop("optional", None)
        if not self.accepts_key:
            call_kwargs.pop("key", None)
        return PreparedCall(
            optional=optional,
            call_kwargs=call_kwargs,
            logged_kwargs=logged_kwargs,
            call_args=args,
        )

    def _parameters_error(
        self,
        ctx: RuntimeContext,
        identity: Identity,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        call_kwargs: dict[str, Any],
        exc: ParametersError,
    ) -> EarlyReturn:
        optional = optional_from_caller(kwargs)
        self._persist_error_row(
            ctx,
            identity,
            optional=optional,
            message=str(exc),
            cause="procedural",
            call_args=args,
            logged_kwargs=call_kwargs,
            exc=exc,
        )
        if optional:
            return EarlyReturn(None)
        raise exc

    def persist_success(
        self,
        ctx: RuntimeContext,
        identity: Identity,
        prepared: PreparedCall,
        value: object,
    ) -> object:
        if isinstance(value, CommandResult):
            result, stored = value, None
        else:
            result = CommandResult(status="PASS", message="", optional=prepared.optional)
            stored = value
        ctx.db.insert_command(
            CommandRow(
                domain=self.domain,
                command=self.command_name,
                key=identity.key_text,
                result=stored,
                status=result.status,
                optional=result.optional,
                message=result.message,
            ),
        )
        ctx.result_aggregator.record_command(
            result,
            key=identity.key_text,
            command=self.command_name,
            domain=self.domain,
        )
        detail = f"value={short_repr(stored)}" if stored is not None else ""
        log_evidence(
            ctx,
            kind="command",
            domain=self.domain,
            command=self.command_name,
            key=identity.key_text,
            status=result.status,
            optional=result.optional,
            detail=detail,
            call_args=prepared.call_args,
            kwargs=prepared.logged_kwargs,
        )
        return value

    def persist_error(
        self,
        ctx: RuntimeContext,
        identity: Identity,
        prepared: PreparedCall,
        exc: Exception,
    ) -> object:
        cause = _command_cause(exc)
        self._persist_error_row(
            ctx,
            identity,
            optional=prepared.optional,
            message=str(exc),
            cause=cause,
            call_args=prepared.call_args,
            logged_kwargs=prepared.logged_kwargs,
            exc=exc,
        )
        if prepared.optional:
            return None
        raise exc

    def _persist_error_row(
        self,
        ctx: RuntimeContext,
        identity: Identity,
        *,
        optional: bool,
        message: str,
        cause: str,
        call_args: tuple[Any, ...],
        logged_kwargs: dict[str, Any],
        exc: Exception,
    ) -> None:
        result = CommandResult(status="ERROR", message=message, optional=optional)
        log_evidence_error(
            ctx,
            kind="command",
            domain=self.domain,
            command=self.command_name,
            key=identity.key_text,
            cause=cause,
            call_args=call_args,
            kwargs=logged_kwargs,
        )
        record_error_event(ctx, domain=self.domain, command=self.command_name, exc=exc)
        ctx.db.insert_command(
            CommandRow(
                domain=self.domain,
                command=self.command_name,
                key=identity.key_text,
                result=None,
                status="ERROR",
                optional=optional,
                message=message,
                cause=cause,
            ),
        )
        ctx.result_aggregator.record_command(
            result,
            key=identity.key_text,
            command=self.command_name,
            domain=self.domain,
            cause=cause,
        )

    def as_spec(self) -> DecoratorSpec:
        return DecoratorSpec(
            kind="command",
            domain=self.domain,
            command=self.command_name,
            func=self.func,
            dry_run=self.dry_run,
            should_skip=self.should_skip,
            resolve_identity=self.resolve_identity,
            dry_run_fields=self.dry_run_fields,
            prepare=self.prepare,
            persist_success=self.persist_success,
            persist_error=self.persist_error,
        )


@overload
def command(func: Callable[P, R], /) -> Callable[P, R]: ...


@overload
def command(
    func: None = None,
    /,
    *,
    dry_run: object = "log",
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def command(_func: Callable[..., Any] | None = None, *, dry_run: object = "log") -> object:
    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        params = signature(func).parameters
        binding = _CommandBinding(
            domain=resolve_domain(func),
            command_name=resolve_command(func),
            func=func,
            dry_run=dry_run,
            accepts_optional="optional" in params,
            accepts_key="key" in params,
        )
        spec = binding.as_spec()

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            return run_decorated_call(spec, *args, **kwargs)

        setattr(wrapper, COLOSSEUM_DECORATOR, "command")
        bind_dry_run_policy(wrapper, dry_run)
        publish_optional_parameter(wrapper, func)
        return wrapper

    if _func is None:
        return decorate
    return decorate(_func)
