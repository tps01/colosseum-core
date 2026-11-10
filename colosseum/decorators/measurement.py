"""Persist decorated call results as SQLite measurement rows."""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from inspect import signature
from typing import TYPE_CHECKING, Any, TypeVar, overload

from colosseum.config.parameters import coerce_optional_kwarg
from colosseum.database import MeasurementRow

from ._common import (
    bind_dry_run_policy,
    finish_dry_run_missing_key,
    missing_key_guidance,
    publish_optional_parameter,
    resolve_auto_key,
    resolve_command,
    resolve_domain,
    should_skip_measurement,
)
from ._kernel import log_evidence, log_evidence_error, record_error_event, short_repr
from ._pipeline import DecoratorSpec, EarlyReturn, Identity, PreparedCall, run_decorated_call
from ._typing import ParamSpec
from .command import COLOSSEUM_DECORATOR, CommandResult

if TYPE_CHECKING:
    from collections.abc import Callable

    from colosseum.context import RuntimeContext

P = ParamSpec("P")
R = TypeVar("R")


class MeasurementKeyError(RuntimeError):
    """Raised when a measurement is missing ``key=`` or duplicates an existing key."""


@dataclass
class _MeasurementBinding:
    domain: str
    command: str
    func: Callable[..., Any]
    dry_run: object
    multi_row: bool
    accepts_optional: bool
    accepts_key: bool

    def should_skip(self, ctx: RuntimeContext) -> bool:
        return should_skip_measurement(ctx)

    def resolve_identity(self, ctx: RuntimeContext, kwargs: dict[str, Any]) -> Identity:
        key, injected = resolve_auto_key(ctx, kwargs, family="measurement")
        key_text = "" if not key else str(key)
        return Identity(key=key, key_text=key_text, injected=injected)

    def before_dry_run(
        self,
        ctx: RuntimeContext,
        identity: Identity,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> EarlyReturn | None:
        if finish_dry_run_missing_key(
            ctx,
            kind="measurement",
            domain=self.domain,
            command=self.command,
            key=identity.key_text,
            call_args=args,
            kwargs=kwargs,
        ):
            return EarlyReturn(None)
        if not identity.key:
            raise MeasurementKeyError(
                missing_key_guidance(kind="measurement", command=self.command),
            )
        return None

    def dry_run_fields(
        self,
        identity: Identity,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "kind": "measurement",
            "domain": self.domain,
            "command": self.command,
            "key": identity.key_text,
            "optional": False,
            "policy": self.dry_run,
            "func": self.func,
            "call_args": args,
            "kwargs": kwargs,
            "injected": identity.injected,
            "pop_key": identity.injected and not self.accepts_key,
            "pop_optional": not self.accepts_optional,
            "multi_row": self.multi_row,
        }

    def after_dry_run(
        self,
        ctx: RuntimeContext,
        identity: Identity,
        kwargs: dict[str, Any],
    ) -> None:
        row_index = int(kwargs.get("row_index", 0))
        identity.row_index = row_index
        if self.multi_row and "row_index" not in kwargs:
            raise MeasurementKeyError(
                f"`{self.command}` with multi_row=True requires `row_index=`",
            )
        self._reject_duplicate(ctx, identity, row_index)

    def _reject_duplicate(
        self,
        ctx: RuntimeContext,
        identity: Identity,
        row_index: int,
    ) -> None:
        key = identity.key
        if not self.multi_row:
            if ctx.db.list_measurements(domain=self.domain, command=self.command, key=key):
                raise MeasurementKeyError(
                    f"Duplicate measurement key for ({self.domain}, {self.command}, {key})",
                )
            return
        if (
            ctx.db.get_measurement(
                domain=self.domain,
                command=self.command,
                key=key,
                row_index=row_index,
            )
            is not None
        ):
            raise MeasurementKeyError(
                f"Duplicate measurement key for ({self.domain}, {self.command}, {key}, " f"row_index={row_index})",
            )

    def prepare(
        self,
        ctx: RuntimeContext,
        identity: Identity,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> PreparedCall | EarlyReturn:
        call_kwargs = dict(kwargs)
        if (
            ctx.parameters_map is not None
            and identity.key_text in ctx.parameters_map
            and "optional" in ctx.parameters_map[identity.key_text]
        ):
            call_kwargs["optional"] = ctx.parameters_map[identity.key_text]["optional"]
        optional = coerce_optional_kwarg(call_kwargs)
        logged_kwargs = dict(call_kwargs)
        if not self.accepts_optional:
            call_kwargs.pop("optional", None)
        if identity.injected and not self.accepts_key:
            call_kwargs.pop("key", None)
        return PreparedCall(
            optional=optional,
            call_kwargs=call_kwargs,
            logged_kwargs=logged_kwargs,
            call_args=args,
            row_index=identity.row_index,
        )

    def persist_success(
        self,
        ctx: RuntimeContext,
        identity: Identity,
        prepared: PreparedCall,
        value: object,
    ) -> object:
        stored = _stored_measurement_value(value)
        row_index = prepared.row_index
        ctx.db.insert_measurement(
            MeasurementRow(
                domain=self.domain,
                command=self.command,
                key=identity.key,
                row_index=row_index,
                value=stored,
                status="PASS",
            ),
        )
        log_evidence(
            ctx,
            kind="measurement",
            domain=self.domain,
            command=self.command,
            key=identity.key,
            status="PASS",
            optional=prepared.optional,
            detail=f"row_index={row_index} value={short_repr(stored)}",
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
        log_evidence_error(
            ctx,
            kind="measurement",
            domain=self.domain,
            command=self.command,
            key=identity.key,
            call_args=prepared.call_args,
            kwargs=prepared.logged_kwargs,
        )
        record_error_event(ctx, domain=self.domain, command=self.command, exc=exc)
        ctx.db.insert_measurement(
            MeasurementRow(
                domain=self.domain,
                command=self.command,
                key=identity.key,
                row_index=prepared.row_index,
                value=None,
                status="ERROR",
            ),
        )
        ctx.result_aggregator.record_measurement(
            CommandResult(status="ERROR", message=str(exc), optional=prepared.optional),
            key=identity.key,
            command=self.command,
            domain=self.domain,
        )
        if prepared.optional:
            return None
        raise exc

    def as_spec(self) -> DecoratorSpec:
        return DecoratorSpec(
            kind="measurement",
            domain=self.domain,
            command=self.command,
            func=self.func,
            dry_run=self.dry_run,
            should_skip=self.should_skip,
            resolve_identity=self.resolve_identity,
            dry_run_fields=self.dry_run_fields,
            prepare=self.prepare,
            persist_success=self.persist_success,
            persist_error=self.persist_error,
            before_dry_run=self.before_dry_run,
            after_dry_run=self.after_dry_run,
        )


def _stored_measurement_value(value: object) -> object:
    if not isinstance(value, (bytes, bytearray)):
        return value
    raw = bytes(value)
    return {
        "encoding": "hex",
        "data": raw.hex(),
        "nbytes": len(raw),
    }


@overload
def measurement(func: Callable[P, R], /) -> Callable[P, R]: ...


@overload
def measurement(
    func: None = None,
    /,
    *,
    multi_row: bool = False,
    dry_run: object = "log",
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def measurement(
    _func: Callable[..., Any] | None = None,
    *,
    multi_row: bool = False,
    dry_run: object = "log",
) -> object:
    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        parameters = signature(func).parameters
        binding = _MeasurementBinding(
            domain=resolve_domain(func),
            command=resolve_command(func),
            func=func,
            dry_run=dry_run,
            multi_row=multi_row,
            accepts_optional="optional" in parameters,
            accepts_key="key" in parameters,
        )
        spec = binding.as_spec()

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            return run_decorated_call(spec, *args, **kwargs)

        setattr(wrapper, COLOSSEUM_DECORATOR, "measurement")
        bind_dry_run_policy(wrapper, dry_run)
        publish_optional_parameter(wrapper, func)
        return wrapper

    if _func is None:
        return decorate
    return decorate(_func)
