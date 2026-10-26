"""Shared helpers for measurement and verification decorators."""

from __future__ import annotations

import sys
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
    toml_value_supported,
)
from colosseum.context import RuntimeContext, get_context
from colosseum.runner.runtime import ensure_runtime_ready
from colosseum.units import coerce_units

from ._kernel import log_evidence, log_evidence_error, short_repr

if TYPE_CHECKING:
    from collections.abc import Callable

_union_type = getattr(types, "UnionType", None)
_UNION_ORIGINS: tuple[Any, ...] = (Union,) if _union_type is None else (Union, _union_type)


def resolve_domain(func: Callable[..., Any]) -> str:
    """Resolve evidence domain from explicit attributes, then parent packages."""
    override = getattr(func, "__colosseum_domain__", None)
    if override:
        return str(override)
    module_name = func.__module__
    parts = module_name.split(".")
    for depth in range(len(parts), 0, -1):
        parent = sys.modules.get(".".join(parts[:depth]))
        if parent is None:
            continue
        domain = getattr(parent, "__colosseum_domain__", None)
        if domain:
            return str(domain)
    return "core"


def stamp_evidence_domain(module: types.ModuleType, name: str) -> None:
    """Set ``__colosseum_domain__`` on the plugin top-level package when unset."""
    module_name = getattr(module, "__name__", "") or ""
    parts = module_name.split(".") if module_name else []
    for depth in range(len(parts), 0, -1):
        parent = sys.modules.get(".".join(parts[:depth]))
        if parent is None:
            continue
        if getattr(parent, "__colosseum_domain__", None):
            return
    if getattr(module, "__colosseum_domain__", None):
        return
    top = parts[0] if parts else ""
    if top and top in sys.modules:
        sys.modules[top].__colosseum_domain__ = name  # type: ignore[attr-defined]
    else:
        module.__colosseum_domain__ = name  # type: ignore[attr-defined]


def command_id_for_module(module: str, name: str) -> str:
    """Derive a command id from a public API module path convention."""
    parts = module.split(".")
    if len(parts) >= 4 and parts[-3] == "io" and parts[-2] == "api":
        group = parts[-1]
        return f"io.{group}.{name}"
    if len(parts) >= 3 and parts[-2] == "api":
        group = parts[-1]
        if not group.startswith("_"):
            return f"{group}.{name}"
    if len(parts) >= 3 and parts[-1] == "api":
        return f"{parts[-2]}.{name}"
    return name


def resolve_command(func: Callable[..., Any]) -> str:
    override = getattr(func, "__colosseum_command__", None)
    if override:
        return str(override)
    return command_id_for_module(func.__module__, func.__name__)


def ensure_runtime_context() -> RuntimeContext:
    ctx = get_context()
    ensure_runtime_ready(ctx)
    return ctx


# execution_mode -> which decorator families are no-ops
_SKIP_BY_MODE: dict[str, frozenset[str]] = {
    "full": frozenset(),
    "procedure": frozenset({"verification"}),
    "verify_only": frozenset({"command", "measurement"}),
}


def _should_skip(ctx: RuntimeContext, family: str) -> bool:
    return family in _SKIP_BY_MODE.get(ctx.active_execution_mode, frozenset())


def should_skip_command(ctx: RuntimeContext) -> bool:
    return _should_skip(ctx, "command")


def should_skip_measurement(ctx: RuntimeContext) -> bool:
    return _should_skip(ctx, "measurement")


def should_skip_verification(ctx: RuntimeContext) -> bool:
    return _should_skip(ctx, "verification")


def resolve_auto_key(
    ctx: RuntimeContext,
    kwargs: dict[str, Any],
    *,
    family: str,
) -> tuple[Any, bool]:
    """Return ``(key, injected)`` for a measurement or verification call.

    An explicit key is returned unchanged. When ``key`` is omitted and
    ``auto_key()`` is enabled, the next integer for ``family`` is written back
    into ``kwargs`` as a decimal string. The first assignment in the procedure
    logs one warning.
    """
    raw = kwargs.get("key")
    if raw:
        return raw, False
    if not ctx.auto_key_enabled:
        return None, False
    if family == "measurement":
        ctx.next_measurement_key += 1
        assigned = ctx.next_measurement_key
    else:
        ctx.next_verification_key += 1
        assigned = ctx.next_verification_key
    key = str(assigned)
    kwargs["key"] = key
    if not ctx.auto_key_warned:
        ctx.auto_key_warned = True
        if ctx.logger is not None:
            ctx.logger.warning(
                "Autokeying has taken place. Later verifications may fail "
                "due to not having the correct keys.",
            )
    return key, True


def _publish_keyword_parameter(
    wrapper: Callable[..., Any],
    func: Callable[..., Any],
    *,
    name: str,
    default: object,
    annotation: object,
) -> None:
    original = signature(func)
    if name in original.parameters:
        return
    parameter = Parameter(
        name,
        kind=Parameter.KEYWORD_ONLY,
        default=default,
        annotation=annotation,
    )
    parameters: list[Parameter] = []
    inserted = False
    for existing in original.parameters.values():
        if not inserted and existing.kind is Parameter.VAR_KEYWORD:
            parameters.append(parameter)
            inserted = True
        parameters.append(existing)
    if not inserted:
        parameters.append(parameter)
    wrapper.__signature__ = original.replace(parameters=parameters)  # type: ignore[attr-defined]


def publish_optional_parameter(wrapper: Callable[..., Any], func: Callable[..., Any]) -> None:
    """Expose keyword-only ``optional: bool = False`` on a decorator wrapper.

    ``inspect.signature`` stops unwrapping when ``__signature__`` is set, so
    ``help()`` and Sphinx list the keyword even when the wrapped function omits it.
    Functions that already declare ``optional`` keep their own signature.
    """
    _publish_keyword_parameter(wrapper, func, name="optional", default=False, annotation=bool)


DRY_RUN_ATTR = "__colosseum_dry_run__"
_EXPORT_OMIT = frozenset({"key", "row_index"})


class _Outcome:
    """Minimal status object accepted by the result aggregator."""

    def __init__(self, status: str, message: str = "", *, optional: bool = False) -> None:
        self.status = status
        self.message = message
        self.optional = optional


def bind_dry_run_policy(wrapper: Callable[..., Any], policy: object) -> None:
    """Store ``dry_run`` on a decorator wrapper.

    ``"log"`` skips the body and records the arguments. ``"call"`` runs the body.
    A callable replaces the body during a dry run.
    """
    if policy != "log" and policy != "call" and not callable(policy):
        raise TypeError(
            "dry_run must be 'log', 'call', or a callable, "
            f"got {type(policy).__name__}",
        )
    setattr(wrapper, DRY_RUN_ATTR, policy)


def _record_outcome(
    ctx: RuntimeContext,
    *,
    kind: str,
    result: _Outcome,
    key: str,
    command: str,
    domain: str,
    description: str = "",
) -> None:
    if kind == "command":
        ctx.result_aggregator.record_command(
            result, key=key, command=command, domain=domain,
        )
        return
    if kind == "measurement":
        ctx.result_aggregator.record_measurement(
            result, key=key, command=command, domain=domain,
        )
        return
    ctx.result_aggregator.record_verification(
        result,
        key=key,
        command=command,
        domain=domain,
        description=description,
    )


def capture_parameter_export(
    ctx: RuntimeContext,
    *,
    kind: str,
    command: str,
    key: str,
    kwargs: dict[str, Any],
) -> bool:
    """Store one keyed call while exporting parameters.

    Returns True when this call should not run. Commands without a key are
    omitted. A measurement or verification without a key is an export error.
    """
    if ctx.parameter_export is None:
        return False
    if not key:
        if kind != "command":
            ctx.export_errors.append(f"`{command}` requires `key=`")
        return True
    section = ctx.parameter_export.setdefault(key, {})
    for name, value in kwargs.items():
        if name in _EXPORT_OMIT:
            continue
        if not toml_value_supported(value):
            ctx.export_errors.append(
                f"key={key!r} field {name} cannot be exported ({type(value).__name__})",
            )
            continue
        section[name] = value
    return True


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
    """Record a missing measurement or verification key and let the walk continue."""
    if not ctx.run_options.dry_run or key:
        return False
    message = f"`{command}` requires `key=`"
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
        seen = any(
            item[0] == domain and item[1] == command and item[2] == key
            for item in ctx.dry_run_measurements
        )
    if seen or not ctx.db.is_initialized():
        return seen
    if multi_row:
        return (
            ctx.db.get_measurement(
                domain=domain, command=command, key=key, row_index=row_index,
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
        hints = {
            name: hint
            for name, hint in getattr(func, "__annotations__", {}).items()
            if not isinstance(hint, str)
        }
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
) -> str | None:
    hints = _hints_for(func)
    for name, value in values.items():
        hint = hints.get(name, Parameter.empty)
        if hint is Parameter.empty or name not in bound.parameters:
            continue
        if _annotation_matches(value, hint):
            continue
        return f"`{name}` must match {_format_hint(hint)}, got {value!r}"
    return None


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
    multi_row: bool,
    require_prior_measurement: bool,
) -> tuple[str | None, dict[str, Any]]:
    """Return a procedure error and the kwargs after the parameters file is applied.

    A parameters-file field overrides the call. ``optional`` is coerced to a bool
    when it is present. The returned mapping still contains bookkeeping names so
    the dry-run record can use the file's ``optional`` and ``description``.
    """
    row_index = 0
    if kind == "measurement":
        if multi_row and "row_index" not in kwargs:
            return f"`{command}` with multi_row=True requires `row_index=`", kwargs
        if multi_row:
            try:
                row_index = int(kwargs["row_index"])
            except (TypeError, ValueError):
                return f"`{command}` row_index must be an integer", kwargs
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
                    f"({domain}, {command}, {key}, row_index={row_index})"
                ), kwargs
            return f"Duplicate measurement key for ({domain}, {command}, {key})", kwargs
    key_in_parameters = ctx.parameters_map is not None and key in ctx.parameters_map
    if (
        require_prior_measurement
        and not key_in_parameters
        and not _evidence_key_measured(ctx, key)
    ):
        return f"no measurement recorded for key={key!r}", kwargs
    call_kwargs = dict(kwargs)
    if apply_parameters and key and not injected:
        try:
            call_kwargs = apply_parameters_to_kwargs(
                call_kwargs,
                key=key,
                parameters=ctx.parameters_map,
            )
        except ParametersError as exc:
            return str(exc), kwargs
    elif (
        key_in_parameters
        and ctx.parameters_map is not None
        and "optional" in ctx.parameters_map[key]
    ):
        call_kwargs["optional"] = ctx.parameters_map[key]["optional"]
    try:
        if "optional" in call_kwargs:
            call_kwargs["optional"] = coerce_bool(call_kwargs["optional"])
    except ParametersError as exc:
        return str(exc), call_kwargs
    resolved = dict(call_kwargs)
    if pop_optional:
        call_kwargs.pop("optional", None)
    if pop_key:
        call_kwargs.pop("key", None)
    if pop_description:
        call_kwargs.pop("description", None)
    # A parameters section may hold limit fields for another call on the same key.
    # Drop file-only names the function does not accept; caller keywords still bind.
    bound = signature(func)
    if not any(item.kind is Parameter.VAR_KEYWORD for item in bound.parameters.values()):
        accepted = set(bound.parameters)
        for name in list(call_kwargs):
            if name not in accepted and name not in kwargs:
                del call_kwargs[name]
    try:
        binding = bound.bind(*call_args, **call_kwargs)
    except TypeError as exc:
        return str(exc), resolved
    binding.apply_defaults()
    try:
        checked = coerce_units(dict(binding.arguments))
    except ValueError as exc:
        return str(exc), resolved
    type_error = _dry_run_type_error(func, bound, checked)
    if type_error is not None:
        return type_error, resolved
    if kind == "measurement" and key:
        ctx.dry_run_measurements.add((domain, command, key, row_index))
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
    injected: bool = False,
    apply_parameters: bool = False,
    pop_key: bool = False,
    pop_optional: bool = False,
    pop_description: bool = False,
    multi_row: bool = False,
    require_prior_measurement: bool = False,
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
        multi_row=multi_row,
        require_prior_measurement=require_prior_measurement,
    )
    if "description" in resolved:
        description = str(resolved["description"]).strip()
    if isinstance(resolved.get("optional"), bool):
        optional = resolved["optional"]
    if message is not None:
        _record_outcome(
            ctx,
            kind=kind,
            result=_Outcome("ERROR", message=message, optional=False),
            key=key,
            command=command,
            domain=domain,
            description=description,
        )
        log_evidence(
            ctx,
            kind=kind,
            domain=domain,
            command=command,
            key=key,
            status="ERROR",
            optional=False,
            detail=f"message={message!r}",
            call_args=call_args,
            kwargs=resolved,
        )
        return True
    _record_outcome(
        ctx,
        kind=kind,
        result=_Outcome("DRY", optional=optional),
        key=key,
        command=command,
        domain=domain,
        description=description,
    )
    log_evidence(
        ctx,
        kind=kind,
        domain=domain,
        command=command,
        key=key,
        status="DRY",
        optional=optional,
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
) -> tuple[bool, Any]:
    """Run a dry-run substitute. ``(False, None)`` means the real body should run."""
    if not ctx.run_options.dry_run or policy == "call" or policy == "log":
        return False, None
    if not callable(policy):
        raise TypeError(
            "dry_run must be 'log', 'call', or a callable, "
            f"got {type(policy).__name__}",
        )
    substitute = cast("Callable[..., Any]", policy)
    try:
        value = substitute(*call_args, **call_kwargs)
    except Exception as exc:  # noqa: BLE001 — substitute failures are recorded, then re-raised
        _record_outcome(
            ctx,
            kind=kind,
            result=_Outcome("ERROR", str(exc)),
            key=key,
            command=command,
            domain=domain,
            description=description,
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
        raise
    _record_outcome(
        ctx,
        kind=kind,
        result=_Outcome("DRY", optional=optional),
        key=key,
        command=command,
        domain=domain,
        description=description,
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


def publish_description_parameter(wrapper: Callable[..., Any], func: Callable[..., Any]) -> None:
    """Expose keyword-only ``description: str = ""`` on a verification wrapper.

    Functions that already declare ``description`` keep their own signature.
    """
    _publish_keyword_parameter(wrapper, func, name="description", default="", annotation=str)
