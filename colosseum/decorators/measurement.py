"""Persist decorated call results as SQLite measurement rows."""

from __future__ import annotations

from functools import wraps
from typing import Callable

from ..context import get_context, init_context, require_context
from ..database import MeasurementRow
from ..output import ensure_output_dir


class MeasurementKeyError(RuntimeError):
    """Raised when a measurement is missing ``key=`` or duplicates an existing key."""


def _resolve_domain(func: Callable) -> str:
    module = func.__module__
    if module.startswith("colosseum_shared"):
        return "shared"
    if module.startswith("colosseum_equipment"):
        return "equipment"
    return getattr(func, "__colosseum_domain__", "core")


def _ensure_ctx_for_call():
    ctx = get_context()
    if ctx is None:
        return init_context(test_case_name="run")
    return ctx


def measurement(_func: Callable | None = None, *, multi_row: bool = False):
    """Decorator that records return values in ``execution.sqlite``.

    Wrapped functions must accept ``key=`` (and ``row_index=`` when ``multi_row=True``).
    Domain and command names are inferred from the defining module.
    """
    def decorate(func: Callable):
        domain = _resolve_domain(func)
        command = func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            ctx = _ensure_ctx_for_call()
            ensure_output_dir(ctx)
            key = kwargs.get("key")
            if not key:
                raise MeasurementKeyError(f"`{command}` requires `key=`")
            row_index = int(kwargs.get("row_index", 0))
            if multi_row and "row_index" not in kwargs:
                raise MeasurementKeyError(f"`{command}` with multi_row=True requires `row_index=`")
            if not multi_row:
                existing = ctx.db.list_measurements(domain=domain, command=command, key=key)
                if existing:
                    raise MeasurementKeyError(f"Duplicate measurement key for ({domain}, {command}, {key})")
            else:
                existing = ctx.db.get_measurement(domain=domain, command=command, key=key, row_index=row_index)
                if existing is not None:
                    raise MeasurementKeyError(
                        f"Duplicate measurement key for ({domain}, {command}, {key}, row_index={row_index})"
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
                    ctx.logger.info("measurement %s.%s key=%s status=PASS", domain, command, key)
                return value
            except Exception as exc:
                if ctx.logger is not None:
                    ctx.logger.exception("measurement %s.%s key=%s status=ERROR", domain, command, key)
                ctx.db.insert_event("ERROR", f"{domain}.{command}", str(exc))
                ctx.db.insert_measurement(
                    MeasurementRow(domain=domain, command=command, key=key, row_index=row_index, value=None, status="ERROR")
                )
                raise

        return wrapper

    if _func is None:
        return decorate
    return decorate(_func)
