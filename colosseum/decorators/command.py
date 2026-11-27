"""Persist decorated command invocations and feed the run result aggregator."""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from inspect import signature
from typing import TYPE_CHECKING, Any, ClassVar, Literal, TypeVar, overload

from colosseum.config.parameters import (
    ParametersError,
    coerce_optional_kwarg,
)
from colosseum.database import CommandRow
from colosseum.exceptions import ProceduralFault

from ._common import (
    bind_dry_run_policy,
    forwarded_kwargs,
    merge_call_parameters,
    optional_from_caller,
    publish_optional_parameter,
    resolve_command,
    resolve_domain,
    should_skip_command,
)
from ._kernel import log_evidence, log_evidence_error, record_error_event, short_repr
from ._pipeline import EarlyReturn, Identity, PreparedCall, run_decorated_call
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
    kind: ClassVar[Literal["command"]] = "command"
    domain: str
    command: str
    func: Callable[..., Any]
    dry_run: object
    wrapper_keywords: frozenset[str]

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
            "command": self.command,
            "key": identity.key_text,
            "optional": False,
            "policy": self.dry_run,
            "func": self.func,
            "call_args": args,
            "kwargs": kwargs,
            "apply_parameters": True,
            "wrapper_keywords": self.wrapper_keywords,
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
            call_kwargs = merge_call_parameters(
                ctx, kwargs, identity.key_text, apply_parameters=True,
            )
            optional = coerce_optional_kwarg(call_kwargs)
        except ParametersError as exc:
            return self._parameters_error(ctx, identity, args, kwargs, call_kwargs, exc)
        return PreparedCall(
            optional=optional,
            call_kwargs=forwarded_kwargs(call_kwargs, self.wrapper_keywords),
            logged_kwargs=call_kwargs,
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
                command=self.command,
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
            command=self.command,
            domain=self.domain,
        )
        detail = f"value={short_repr(stored)}" if stored is not None else ""
        log_evidence(
            ctx,
            kind="command",
            domain=self.domain,
            command=self.command,
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
            command=self.command,
            key=identity.key_text,
            cause=cause,
            optional=optional,
            call_args=call_args,
            kwargs=logged_kwargs,
        )
        record_error_event(ctx, domain=self.domain, command=self.command, exc=exc)
        ctx.db.insert_command(
            CommandRow(
                domain=self.domain,
                command=self.command,
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
            command=self.command,
            domain=self.domain,
            cause=cause,
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
            command=resolve_command(func),
            func=func,
            dry_run=dry_run,
            wrapper_keywords=frozenset({"key", "optional"}.difference(params)),
        )

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            return run_decorated_call(binding, *args, **kwargs)

        setattr(wrapper, COLOSSEUM_DECORATOR, "command")
        bind_dry_run_policy(wrapper, dry_run)
        publish_optional_parameter(wrapper, func)
        return wrapper

    if _func is None:
        return decorate
    return decorate(_func)
