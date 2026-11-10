"""Dry-run engine for decorated calls: structure checks, logging, and substitutes."""

from __future__ import annotations

import types
from inspect import Parameter, Signature, signature
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Literal,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from colosseum.config.parameters import (
    ParametersError,
    apply_parameters_to_kwargs,
    coerce_bool,
)
from colosseum.units import coerce_units

from ._common import missing_key_guidance, note_dry_run_tip
from ._kernel import log_evidence, log_evidence_error, short_repr

if TYPE_CHECKING:
    from collections.abc import Callable

    from colosseum.context import RuntimeContext

_union_type = getattr(types, "UnionType", None)
_UNION_ORIGINS: tuple[Any, ...] = (Union,) if _union_type is None else (Union, _union_type)


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


def _evidence_key_measured(ctx: RuntimeContext, key: str) -> bool:
    """Return whether a dry-run walk or the database already has this evidence key."""
    if any(item[2] == key for item in ctx.dry_run_measurements):
        return True
    if not ctx.db.is_initialized():
        return False
    return key in ctx.db.measurement_keys()


def _hints_for(func: Callable[..., Any]) -> dict[str, Any]:
    """Return resolved annotations. An annotation that cannot be resolved is omitted."""
    try:
        hints = get_type_hints(func)
    except Exception:  # noqa: BLE001 — unresolved forward references stay unchecked
        hints = {name: hint for name, hint in getattr(func, "__annotations__", {}).items() if not isinstance(hint, str)}
    hints.pop("return", None)
    return hints


def _annotation_matches(value: object, hint: object) -> bool:
    """Return whether ``value`` agrees with a minimal reading of ``hint``."""
    if hint is Any or hint is Parameter.empty:
        return True
    origin = get_origin(hint)
    if origin in _UNION_ORIGINS:
        return any(_annotation_matches(value, item) for item in get_args(hint))
    if origin is Literal:
        return any(value == item and type(value) is type(item) for item in get_args(hint))
    if origin is Annotated:
        args = get_args(hint)
        return _annotation_matches(value, args[0]) if args else True
    if isinstance(origin, type):
        return _isinstance_hint(value, origin)
    if origin is not None:
        return True
    if hint is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if hint is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if isinstance(hint, type):
        return _isinstance_hint(value, hint)
    return True


def _isinstance_hint(value: object, hint: type[Any]) -> bool:
    try:
        return isinstance(value, hint)
    except TypeError:
        return True


def _format_hint(hint: object) -> str:
    if hint is type(None):
        return "None"
    if isinstance(hint, type):
        return hint.__name__
    return str(hint).replace("typing.", "")


def _dry_run_type_error(
    func: Callable[..., Any],
    bound: Signature,
    values: dict[str, Any],
    *,
    key: str = "",
    from_parameters: bool = False,
) -> str | None:
    hints = _hints_for(func)
    for name, value in values.items():
        hint = hints.get(name, Parameter.empty)
        if hint is Parameter.empty or name not in bound.parameters:
            continue
        if _annotation_matches(value, hint):
            continue
        message = f"`{name}` must match {_format_hint(hint)}, got {value!r}"
        if from_parameters and key:
            message += f" (from parameters[{key!r}])"
        return message
    return None


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


def _dry_run_apply_parameters(
    ctx: RuntimeContext,
    *,
    key: str,
    kwargs: dict[str, Any],
    injected: bool,
    apply_parameters: bool,
) -> tuple[str | None, dict[str, Any], bool, bool]:
    """Apply the parameters file and coerce ``optional`` when present."""
    key_in_parameters = bool(key) and ctx.parameters_map is not None and key in ctx.parameters_map
    call_kwargs = dict(kwargs)
    applied_parameters = False
    if apply_parameters and key and not injected:
        try:
            before = dict(call_kwargs)
            call_kwargs = apply_parameters_to_kwargs(
                call_kwargs,
                key=key,
                parameters=ctx.parameters_map,
            )
            applied_parameters = call_kwargs != before
        except ParametersError as exc:
            return str(exc), kwargs, False, key_in_parameters
    elif key_in_parameters and ctx.parameters_map is not None and "optional" in ctx.parameters_map[key]:
        call_kwargs["optional"] = ctx.parameters_map[key]["optional"]
    try:
        if "optional" in call_kwargs:
            call_kwargs["optional"] = coerce_bool(call_kwargs["optional"])
    except ParametersError as exc:
        return str(exc), call_kwargs, applied_parameters, key_in_parameters
    return None, call_kwargs, applied_parameters, key_in_parameters


def _dry_run_filter_call_kwargs(
    *,
    kind: str,
    key: str,
    func: Callable[..., Any],
    kwargs: dict[str, Any],
    call_kwargs: dict[str, Any],
    pop_key: bool,
    pop_optional: bool,
    pop_description: bool,
    pop_requirements: bool,
) -> Signature:
    """Strip wrapper-owned names and drop file-only extras the body rejects."""
    if pop_optional:
        call_kwargs.pop("optional", None)
    if pop_key:
        call_kwargs.pop("key", None)
    elif kind == "verification" and not key:
        # Match live mode: inject blank key so signature.bind succeeds.
        call_kwargs["key"] = ""
    if pop_description:
        call_kwargs.pop("description", None)
    if pop_requirements:
        call_kwargs.pop("requirements", None)
    # A parameters section may hold limit fields for another call on the same key.
    # Drop file-only names the function does not accept; caller keywords still bind.
    bound = signature(func)
    if not any(item.kind is Parameter.VAR_KEYWORD for item in bound.parameters.values()):
        accepted = set(bound.parameters)
        for name in list(call_kwargs):
            if name not in accepted and name not in kwargs:
                del call_kwargs[name]
    return bound


def _dry_run_note_structure(
    ctx: RuntimeContext,
    *,
    kind: str,
    domain: str,
    command: str,
    key: str,
    row_index: int,
) -> None:
    if kind == "measurement" and key:
        ctx.dry_run_measurements.add((domain, command, key, row_index))
    if key:
        ctx.note_parameter_use(key)


def _dry_run_bind_and_typecheck(
    ctx: RuntimeContext,
    *,
    kind: str,
    domain: str,
    command: str,
    key: str,
    func: Callable[..., Any],
    call_args: tuple[Any, ...],
    kwargs: dict[str, Any],
    call_kwargs: dict[str, Any],
    pop_key: bool,
    pop_optional: bool,
    pop_description: bool,
    pop_requirements: bool,
    key_in_parameters: bool,
    applied_parameters: bool,
    row_index: int,
) -> tuple[str | None, dict[str, Any]]:
    """Filter wrapper kwargs, bind the user signature, and type-check values."""
    resolved = dict(call_kwargs)
    bound = _dry_run_filter_call_kwargs(
        kind=kind,
        key=key,
        func=func,
        kwargs=kwargs,
        call_kwargs=call_kwargs,
        pop_key=pop_key,
        pop_optional=pop_optional,
        pop_description=pop_description,
        pop_requirements=pop_requirements,
    )
    try:
        binding = bound.bind(*call_args, **call_kwargs)
    except TypeError as exc:
        message = f"`{command}` call did not match its signature: {exc}"
        if key_in_parameters:
            message += f"; check parameters[{key!r}] fields against the function signature"
        return message, resolved
    binding.apply_defaults()
    try:
        checked = coerce_units(dict(binding.arguments))
    except ValueError as exc:
        return str(exc), resolved
    type_error = _dry_run_type_error(
        func,
        bound,
        checked,
        key=key,
        from_parameters=applied_parameters or key_in_parameters,
    )
    if type_error is not None:
        return type_error, resolved
    _dry_run_note_structure(
        ctx,
        kind=kind,
        domain=domain,
        command=command,
        key=key,
        row_index=row_index,
    )
    return None, resolved


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
    injected: bool,
    apply_parameters: bool,
    pop_key: bool,
    pop_optional: bool,
    pop_description: bool,
    pop_requirements: bool,
    multi_row: bool,
) -> tuple[str | None, dict[str, Any]]:
    """Return a procedure error and the kwargs after the parameters file is applied.

    A parameters-file field overrides the call. ``optional`` is coerced to a bool
    when it is present. The returned mapping still contains bookkeeping names so
    the dry-run record can use the file's ``optional`` and ``description``.
    """
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
    apply_error, call_kwargs, applied_parameters, key_in_parameters = _dry_run_apply_parameters(
        ctx,
        key=key,
        kwargs=kwargs,
        injected=injected,
        apply_parameters=apply_parameters,
    )
    if apply_error is not None:
        return apply_error, call_kwargs
    return _dry_run_bind_and_typecheck(
        ctx,
        kind=kind,
        domain=domain,
        command=command,
        key=key,
        func=func,
        call_args=call_args,
        kwargs=kwargs,
        call_kwargs=call_kwargs,
        pop_key=pop_key,
        pop_optional=pop_optional,
        pop_description=pop_description,
        pop_requirements=pop_requirements,
        key_in_parameters=key_in_parameters,
        applied_parameters=applied_parameters,
        row_index=row_index,
    )


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
    injected: bool = False,
    apply_parameters: bool = False,
    pop_key: bool = False,
    pop_optional: bool = False,
    pop_description: bool = False,
    pop_requirements: bool = False,
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
        injected=injected,
        apply_parameters=apply_parameters,
        pop_key=pop_key,
        pop_optional=pop_optional,
        pop_description=pop_description,
        pop_requirements=pop_requirements,
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
    if (
        message is None
        and kind == "verification"
        and key
        and not _evidence_key_measured(ctx, key)
        and not (ctx.parameters_map is not None and key in ctx.parameters_map)
    ):
        note_dry_run_tip(
            ctx,
            f"`{command}` verification key={key!r} has no measurement in this "
            "walk yet; measure first, or use missing_measurement_result in the "
            "body for live",
        )
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
