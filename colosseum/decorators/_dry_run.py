"""Dry-run engine for decorated calls: structure checks, logging, and substitutes."""

from __future__ import annotations

from inspect import Parameter, signature
from typing import (
    TYPE_CHECKING,
    Any,
    cast,
)

from colosseum.config.parameters import (
    ParametersError,
    coerce_optional_kwarg,
)
from colosseum.units import coerce_units

from ._common import forwarded_kwargs, merge_call_parameters, missing_key_guidance
from ._kernel import log_evidence, log_evidence_error, short_repr

if TYPE_CHECKING:
    from collections.abc import Callable

    from colosseum.context import RuntimeContext


class _Outcome:
    """Minimal status object accepted by the result aggregator."""

    def __init__(self, status: str, message: str = "", *, optional: bool = False) -> None:
        self.status = status
        self.message = message
        self.optional = optional


def _record_outcome(
    ctx: RuntimeContext,
    *,
    kind: str,
    result: _Outcome,
    key: str,
    command: str,
    domain: str,
    description: str = "",
    requirements: list[str] | None = None,
) -> None:
    if kind == "command":
        ctx.result_aggregator.record_command(
            result,
            key=key,
            command=command,
            domain=domain,
        )
        return
    if kind == "measurement":
        ctx.result_aggregator.record_measurement(
            result,
            key=key,
            command=command,
            domain=domain,
        )
        return
    ctx.result_aggregator.record_verification(
        result,
        key=key,
        command=command,
        domain=domain,
        description=description,
        requirements=requirements,
    )


def finish_dry_run_missing_key(
    ctx: RuntimeContext,
    *,
    kind: str,
    domain: str,
    command: str,
    key: str,
    call_args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> bool:
    """Record a missing measurement key and let the walk continue."""
    if not ctx.run_options.dry_run or key:
        return False
    message = missing_key_guidance(kind=kind, command=command)
    _record_outcome(
        ctx,
        kind=kind,
        result=_Outcome("ERROR", message),
        key="",
        command=command,
        domain=domain,
    )
    log_evidence(
        ctx,
        kind=kind,
        domain=domain,
        command=command,
        key="",
        status="ERROR",
        detail=f"message={message!r}",
        call_args=call_args,
        kwargs=kwargs,
    )
    return True


def _measurement_already_logged(
    ctx: RuntimeContext,
    *,
    domain: str,
    command: str,
    key: str,
    row_index: int,
    multi_row: bool,
) -> bool:
    """Return whether this measurement identity was already visited or stored."""
    if multi_row:
        seen = (domain, command, key, row_index) in ctx.dry_run_measurements
    else:
        seen = any(item[0] == domain and item[1] == command and item[2] == key for item in ctx.dry_run_measurements)
    if seen or not ctx.db.is_initialized():
        return seen
    if multi_row:
        return (
            ctx.db.get_measurement(
                domain=domain,
                command=command,
                key=key,
                row_index=row_index,
            )
            is not None
        )
    return bool(ctx.db.list_measurements(domain=domain, command=command, key=key))


def _dry_run_measurement_precheck(
    ctx: RuntimeContext,
    *,
    kind: str,
    domain: str,
    command: str,
    key: str,
    kwargs: dict[str, Any],
    multi_row: bool,
) -> tuple[str | None, int]:
    """Validate measurement identity before the parameters file is applied."""
    row_index = 0
    if kind == "measurement":
        if multi_row and "row_index" not in kwargs:
            return (
                f"`{command}` with multi_row=True requires `row_index=` (an integer per row)",
                row_index,
            )
        if multi_row:
            try:
                row_index = int(kwargs["row_index"])
            except (TypeError, ValueError):
                return f"`{command}` row_index must be an integer per row", row_index
        if _measurement_already_logged(
            ctx,
            domain=domain,
            command=command,
            key=key,
            row_index=row_index,
            multi_row=multi_row,
        ):
            if multi_row:
                return (
                    f"Duplicate measurement key for "
                    f"({domain}, {command}, {key}, row_index={row_index}); "
                    "use a unique key= or distinct row_index="
                ), row_index
            return (
                f"Duplicate measurement key for ({domain}, {command}, {key}); "
                "use a unique key= or @measurement(..., multi_row=True) with "
                "distinct row_index="
            ), row_index
    return None, row_index


def _dry_run_structure_message(
    ctx: RuntimeContext,
    *,
    kind: str,
    domain: str,
    command: str,
    key: str,
    func: Callable[..., Any],
    call_args: tuple[Any, ...],
    kwargs: dict[str, Any],
    apply_parameters: bool,
    wrapper_keywords: frozenset[str],
    multi_row: bool,
) -> tuple[str | None, dict[str, Any]]:
    """Check the body signature and units while retaining resolved evidence inputs."""
    precheck_error, row_index = _dry_run_measurement_precheck(
        ctx,
        kind=kind,
        domain=domain,
        command=command,
        key=key,
        kwargs=kwargs,
        multi_row=multi_row,
    )
    if precheck_error is not None:
        return precheck_error, kwargs
    resolved = kwargs
    try:
        resolved = merge_call_parameters(
            ctx, kwargs, key, apply_parameters=apply_parameters, optional_only=bool(key),
        )
        coerce_optional_kwarg(resolved)
    except ParametersError as exc:
        return str(exc), resolved

    body_kwargs = forwarded_kwargs(resolved, wrapper_keywords)
    if kind == "verification" and not key and "key" not in wrapper_keywords:
        body_kwargs["key"] = ""
    bound = signature(func)
    # A section can also contain fields for another call using the same key.
    if not any(param.kind is Parameter.VAR_KEYWORD for param in bound.parameters.values()):
        body_kwargs = {
            name: value for name, value in body_kwargs.items()
            if name in bound.parameters or name in kwargs
        }
    try:
        binding = bound.bind(*call_args, **body_kwargs)
    except TypeError as exc:
        message = f"`{command}` call did not match its signature: {exc}"
        if key and ctx.parameters_map is not None and key in ctx.parameters_map:
            message += f"; check parameters[{key!r}] fields against the function signature"
        return message, resolved
    binding.apply_defaults()
    try:
        coerce_units(dict(binding.arguments), func=func)
    except ValueError as exc:
        return str(exc), resolved
    if kind == "measurement" and key:
        ctx.dry_run_measurements.add((domain, command, key, row_index))
    if key:
        ctx.note_parameter_use(key)
    return None, resolved


def finish_dry_run_log(
    ctx: RuntimeContext,
    *,
    kind: str,
    domain: str,
    command: str,
    key: str,
    optional: bool,
    policy: object,
    func: Callable[..., Any],
    call_args: tuple[Any, ...],
    kwargs: dict[str, Any],
    description: str = "",
    requirements: list[str] | None = None,
    apply_parameters: bool = False,
    wrapper_keywords: frozenset[str] = frozenset(),
    multi_row: bool = False,
) -> bool:
    """Check structure, log the call, and skip the body when the policy is ``log``."""
    if not ctx.run_options.dry_run or policy != "log":
        return False
    message, resolved = _dry_run_structure_message(
        ctx,
        kind=kind,
        domain=domain,
        command=command,
        key=key,
        func=func,
        call_args=call_args,
        kwargs=kwargs,
        apply_parameters=apply_parameters,
        wrapper_keywords=wrapper_keywords,
        multi_row=multi_row,
    )
    if "description" in resolved:
        description = str(resolved["description"]).strip()
    if isinstance(resolved.get("optional"), bool):
        optional = resolved["optional"]
    req_ids = list(requirements or [])
    if "requirements" in resolved:
        try:
            from colosseum.results.aggregation import coerce_requirements

            req_ids = coerce_requirements(resolved["requirements"])
        except TypeError as exc:
            message = str(exc) if message is None else message
            req_ids = []
    if message is not None:
        result = _Outcome("ERROR", message=message, optional=False)
    else:
        result = _Outcome("DRY", optional=optional)
    _record_outcome(
        ctx,
        kind=kind,
        result=result,
        key=key,
        command=command,
        domain=domain,
        description=description,
        requirements=req_ids,
    )
    log_evidence(
        ctx,
        kind=kind,
        domain=domain,
        command=command,
        key=key,
        status=result.status,
        optional=result.optional,
        detail=f"message={message!r}" if message is not None else "",
        call_args=call_args,
        kwargs=resolved,
    )
    return True


def invoke_dry_run_substitute(
    ctx: RuntimeContext,
    *,
    kind: str,
    domain: str,
    command: str,
    key: str,
    optional: bool,
    policy: object,
    call_args: tuple[Any, ...],
    call_kwargs: dict[str, Any],
    logged_kwargs: dict[str, Any],
    description: str = "",
    requirements: list[str] | None = None,
) -> tuple[bool, Any]:
    """Run a dry-run substitute. ``(False, None)`` means the real body should run."""
    if not ctx.run_options.dry_run or policy == "call" or policy == "log":
        return False, None
    if not callable(policy):
        raise TypeError(
            f"dry_run must be 'log', 'call', or a callable, got {type(policy).__name__}",
        )
    substitute = cast("Callable[..., Any]", policy)
    try:
        value = substitute(*call_args, **call_kwargs)
    except Exception as exc:  # noqa: BLE001 — match live optional / verification policy
        _record_outcome(
            ctx,
            kind=kind,
            result=_Outcome("ERROR", str(exc), optional=optional),
            key=key,
            command=command,
            domain=domain,
            description=description,
            requirements=requirements,
        )
        log_evidence_error(
            ctx,
            kind=kind,
            domain=domain,
            command=command,
            key=key,
            optional=optional,
            call_args=call_args,
            kwargs=logged_kwargs,
        )
        if kind == "verification":
            from colosseum.decorators.tolerance import VerificationResult

            return True, VerificationResult(
                status="ERROR",
                message=str(exc),
                optional=optional,
            )
        if optional:
            return True, None
        raise
    _record_outcome(
        ctx,
        kind=kind,
        result=_Outcome("DRY", optional=optional),
        key=key,
        command=command,
        domain=domain,
        description=description,
        requirements=requirements,
    )
    log_evidence(
        ctx,
        kind=kind,
        domain=domain,
        command=command,
        key=key,
        status="DRY",
        optional=optional,
        detail=f"value={short_repr(value)}",
        call_args=call_args,
        kwargs=logged_kwargs,
    )
    return True, value
