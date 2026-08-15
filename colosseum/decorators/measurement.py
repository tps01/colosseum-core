"""Persist decorated call results as SQLite measurement rows."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, overload

from ..database import MeasurementRow
from ..output import ensure_runtime_ready
from ._common import ensure_runtime_context, resolve_command, resolve_domain
from ._typing import ParamSpec
from .command import COLOSSEUM_DECORATOR

P = ParamSpec("P")
R = TypeVar("R")


class MeasurementKeyError(RuntimeError):
    """Raised when a measurement is missing ``key=`` or duplicates an existing key."""


@overload
def measurement(func: Callable[P, R], /) -> Callable[P, R]: ...


@overload
def measurement(
    func: None = None, /, *, multi_row: bool = False
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def measurement(
    _func: Callable[..., Any] | None = None, *, multi_row: bool = False
) -> object:
    """Decorator that records return values in ``execution.sqlite``.

    Wrapped functions must accept ``key=`` (and ``row_index=`` when ``multi_row=True``).
    Domain and command names are inferred from the defining module. First-party
    APIs include their public group in the command name, such as
    ``dmm.measure_voltage`` or ``psu.measure_voltage``.

    :param _func: Function to wrap when used as ``@measurement`` without parentheses.
    :type _func: Callable | None
    :param multi_row: When ``True``, allow multiple rows per key using ``row_index=``.
    :type multi_row: bool

    :returns: The decorated callable. Re-raises exceptions after recording ERROR.
    """

    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        domain = resolve_domain(func)
        command = resolve_command(func)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            ctx = ensure_runtime_context()
            ensure_runtime_ready(ctx)
            key = kwargs.get("key")
            if not key:
                raise MeasurementKeyError(f"`{command}` requires `key=`")
            row_index = int(kwargs.get("row_index", 0))
            if multi_row and "row_index" not in kwargs:
                raise MeasurementKeyError(f"`{command}` with multi_row=True requires `row_index=`")
            if not multi_row:
                existing_rows = ctx.db.list_measurements(domain=domain, command=command, key=key)
                if existing_rows:
                    raise MeasurementKeyError(
                        f"Duplicate measurement key for ({domain}, {command}, {key})"
                    )
            else:
                existing_row = ctx.db.get_measurement(
                    domain=domain, command=command, key=key, row_index=row_index
                )
                if existing_row is not None:
                    raise MeasurementKeyError(
                        f"Duplicate measurement key for ({domain}, {command}, {key}, "
                        f"row_index={row_index})"
                    )
            try:
                value = func(*args, **kwargs)
                ctx.db.insert_measurement(
                    MeasurementRow(
                        domain=domain,
                        command=command,
                        key=key,
                        row_index=row_index,
                        value=value,
                        status="PASS",
                    )
                )
                if ctx.logger is not None:
                    value_repr = repr(value)
                    if len(value_repr) > 120:
                        value_repr = value_repr[:117] + "..."
                    ctx.logger.debug(
                        "measurement %s.%s key=%s row_index=%s value=%s",
                        domain,
                        command,
                        key,
                        row_index,
                        value_repr,
                    )
                    ctx.logger.info("measurement %s.%s key=%s status=PASS", domain, command, key)
                return value
            except Exception as exc:
                if ctx.logger is not None:
                    ctx.logger.exception(
                        "measurement %s.%s key=%s status=ERROR", domain, command, key
                    )
                ctx.db.insert_event("ERROR", f"{domain}.{command}", str(exc))
                ctx.db.insert_measurement(
                    MeasurementRow(
                        domain=domain,
                        command=command,
                        key=key,
                        row_index=row_index,
                        value=None,
                        status="ERROR",
                    )
                )
                raise

        setattr(wrapper, COLOSSEUM_DECORATOR, "measurement")
        return wrapper

    if _func is None:
        return decorate
    return decorate(_func)
