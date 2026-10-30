"""Persist decorated call results as SQLite measurement rows."""

from __future__ import annotations

from functools import wraps
from inspect import signature
from typing import TYPE_CHECKING, Any, TypeVar, overload

from colosseum.config.parameters import coerce_optional_kwarg
from colosseum.database import MeasurementRow
from colosseum.units import coerce_units

from ._common import (
    bind_dry_run_policy,
    capture_parameter_export,
    ensure_runtime_context,
    finish_dry_run_log,
    finish_dry_run_missing_key,
    invoke_dry_run_substitute,
    missing_key_guidance,
    publish_optional_parameter,
    resolve_auto_key,
    resolve_command,
    resolve_domain,
    should_skip_measurement,
)
from ._kernel import log_evidence, log_evidence_error, record_error_event, short_repr
from ._typing import ParamSpec
from .command import COLOSSEUM_DECORATOR, CommandResult

if TYPE_CHECKING:
    from collections.abc import Callable

P = ParamSpec("P")
R = TypeVar("R")


class MeasurementKeyError(RuntimeError):
    """Raised when a measurement is missing ``key=`` or duplicates an existing key."""


@overload
def measurement(func: Callable[P, R], /) -> Callable[P, R]: ...


@overload
def measurement(
    func: None = None, /, *, multi_row: bool = False, dry_run: object = "log",
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def measurement(
    _func: Callable[..., Any] | None = None,
    *,
    multi_row: bool = False,
    dry_run: object = "log",
) -> object:
    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        domain = resolve_domain(func)
        command = resolve_command(func)
        parameters = signature(func).parameters
        accepts_optional = "optional" in parameters
        accepts_key = "key" in parameters

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            ctx = ensure_runtime_context()
            if should_skip_measurement(ctx):
                return None
            key, injected = resolve_auto_key(ctx, kwargs, family="measurement")
            key_text = "" if not key else str(key)
            if capture_parameter_export(
                ctx, kind="measurement", command=command, key=key_text, kwargs=kwargs,
            ):
                return None
            if finish_dry_run_missing_key(
                ctx,
                kind="measurement",
                domain=domain,
                command=command,
                key=key_text,
                call_args=args,
                kwargs=kwargs,
            ):
                return None
            if not key:
                raise MeasurementKeyError(
                    missing_key_guidance(kind="measurement", command=command),
                )
            if finish_dry_run_log(
                ctx,
                kind="measurement",
                domain=domain,
                command=command,
                key=key_text,
                optional=False,
                policy=dry_run,
                func=func,
                call_args=args,
                kwargs=kwargs,
                injected=injected,
                pop_key=injected and not accepts_key,
                pop_optional=not accepts_optional,
                multi_row=multi_row,
            ):
                return None
            row_index = int(kwargs.get("row_index", 0))
            if multi_row and "row_index" not in kwargs:
                raise MeasurementKeyError(f"`{command}` with multi_row=True requires `row_index=`")
            if not multi_row:
                if ctx.db.list_measurements(domain=domain, command=command, key=key):
                    raise MeasurementKeyError(
                        f"Duplicate measurement key for ({domain}, {command}, {key})",
                    )
            elif (
                ctx.db.get_measurement(
                    domain=domain, command=command, key=key, row_index=row_index,
                )
                is not None
            ):
                raise MeasurementKeyError(
                    f"Duplicate measurement key for ({domain}, {command}, {key}, "
                    f"row_index={row_index})",
                )
            call_kwargs = dict(kwargs)
            if (
                ctx.parameters_map is not None
                and key_text in ctx.parameters_map
                and "optional" in ctx.parameters_map[key_text]
            ):
                call_kwargs["optional"] = ctx.parameters_map[key_text]["optional"]
            optional = coerce_optional_kwarg(call_kwargs)
            logged_kwargs = dict(call_kwargs)
            if not accepts_optional:
                call_kwargs.pop("optional", None)
            if injected and not accepts_key:
                call_kwargs.pop("key", None)
            handled, value = invoke_dry_run_substitute(
                ctx,
                kind="measurement",
                domain=domain,
                command=command,
                key=key_text,
                optional=optional,
                policy=dry_run,
                call_args=args,
                call_kwargs=call_kwargs,
                logged_kwargs=logged_kwargs,
            )
            if handled:
                return value
            try:
                call_kwargs = coerce_units(call_kwargs)
                value = func(*args, **call_kwargs)
                # Persist a JSON-safe form for bytes while returning the original value.
                stored: Any = value
                if isinstance(value, (bytes, bytearray)):
                    raw = bytes(value)
                    stored = {
                        "encoding": "hex",
                        "data": raw.hex(),
                        "nbytes": len(raw),
                    }
                ctx.db.insert_measurement(
                    MeasurementRow(
                        domain=domain,
                        command=command,
                        key=key,
                        row_index=row_index,
                        value=stored,
                        status="PASS",
                    ),
                )
                log_evidence(
                    ctx,
                    kind="measurement",
                    domain=domain,
                    command=command,
                    key=key,
                    status="PASS",
                    optional=optional,
                    detail=f"row_index={row_index} value={short_repr(stored)}",
                    call_args=args,
                    kwargs=logged_kwargs,
                )
                return value
            except Exception as exc:
                log_evidence_error(
                    ctx,
                    kind="measurement",
                    domain=domain,
                    command=command,
                    key=key,
                    call_args=args,
                    kwargs=logged_kwargs,
                )
                record_error_event(ctx, domain=domain, command=command, exc=exc)
                ctx.db.insert_measurement(
                    MeasurementRow(
                        domain=domain,
                        command=command,
                        key=key,
                        row_index=row_index,
                        value=None,
                        status="ERROR",
                    ),
                )
                ctx.result_aggregator.record_measurement(
                    CommandResult(status="ERROR", message=str(exc), optional=optional),
                    key=key,
                    command=command,
                    domain=domain,
                )
                if optional:
                    return None
                raise

        setattr(wrapper, COLOSSEUM_DECORATOR, "measurement")
        bind_dry_run_policy(wrapper, dry_run)
        publish_optional_parameter(wrapper, func)
        return wrapper

    if _func is None:
        return decorate
    return decorate(_func)
