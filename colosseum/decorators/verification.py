"""Persist decorated verification results and feed the run result aggregator."""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from typing import Callable, Iterable, Optional

from ..context import get_context, init_context
from ..database import VerificationRow
from ..output import ensure_output_dir


@dataclass(frozen=True)
class MeasurementSource:
    """Link a verification to a prior measurement ``domain`` and ``command``."""

    domain: str
    command: str


@dataclass
class VerificationResult:
    """Outcome returned by ``@verification`` functions (``PASS``, ``FAIL``, or ``ERROR``)."""

    status: str
    message: str = ""
    optional: bool = False


def _resolve_domain(func: Callable) -> str:
    module = func.__module__
    if module.startswith("colosseum_shared"):
        return "shared"
    if module.startswith("colosseum_equipment"):
        return "equipment"
    return getattr(func, "__colosseum_domain__", "core")


def _ensure_ctx():
    ctx = get_context()
    if ctx is None:
        ctx = init_context(test_case_name="run")
    return ctx


def verification(
    _func: Optional[Callable] = None,
    *,
    sources: Optional[Iterable[MeasurementSource]] = None,
):
    """Decorator that records verification rows and updates exit aggregation.

    Wrapped functions must accept ``key=`` and return :class:`VerificationResult` (or
    ``bool``). Use ``sources=`` to require measurements before the check runs.
    """
    source_list = list(sources or [])

    def decorate(func: Callable):
        domain = _resolve_domain(func)
        command = func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            ctx = _ensure_ctx()
            ensure_output_dir(ctx)
            key = kwargs.get("key")
            optional = bool(kwargs.get("optional", False))
            if not key:
                result = VerificationResult(status="ERROR", message=f"`{command}` requires `key=`", optional=optional)
                ctx.result_aggregator.record_verification(
                    result, key="", command=command, domain=domain
                )
                ctx.db.insert_verification(
                    VerificationRow(
                        domain=domain,
                        command=command,
                        key="<missing>",
                        expected=None,
                        actual=None,
                        status=result.status,
                        optional=result.optional,
                        message=result.message,
                    )
                )
                return result
            for source in source_list:
                if ctx.db.get_measurement(source.domain, source.command, key, row_index=int(kwargs.get("row_index", 0))) is None:
                    result = VerificationResult(
                        status="ERROR",
                        message=f"Missing measurement source {source.domain}.{source.command} key={key}",
                        optional=optional,
                    )
                    ctx.result_aggregator.record_verification(
                        result, key=str(key), command=command, domain=domain
                    )
                    ctx.db.insert_verification(
                        VerificationRow(
                            domain=domain,
                            command=command,
                            key=key,
                            expected=kwargs.get("expected_val"),
                            actual=None,
                            status=result.status,
                            optional=result.optional,
                            message=result.message,
                        )
                    )
                    return result
            try:
                raw_result = func(*args, **kwargs)
                if isinstance(raw_result, VerificationResult):
                    result = raw_result
                elif isinstance(raw_result, bool):
                    result = VerificationResult(
                        status="PASS" if raw_result else "FAIL",
                        message="" if raw_result else "verification returned False",
                        optional=optional,
                    )
                else:
                    result = VerificationResult(status="PASS", message=str(raw_result), optional=optional)
            except Exception as exc:
                result = VerificationResult(status="ERROR", message=str(exc), optional=optional)
            ctx.result_aggregator.record_verification(
                result, key=str(key), command=command, domain=domain
            )
            ctx.db.insert_verification(
                VerificationRow(
                    domain=domain,
                    command=command,
                    key=key,
                    expected=kwargs.get("expected_val"),
                    actual=None,
                    status=result.status,
                    optional=result.optional,
                    message=result.message,
                )
            )
            if ctx.logger is not None:
                ctx.logger.info(
                    "verification %s.%s key=%s status=%s optional=%s",
                    domain,
                    command,
                    key,
                    result.status,
                    result.optional,
                )
            return result

        return wrapper

    if _func is None:
        return decorate
    return decorate(_func)
