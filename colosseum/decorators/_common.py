"""Shared helpers for measurement and verification decorators."""

from __future__ import annotations

import sys
from inspect import Parameter, signature
from typing import TYPE_CHECKING, Any

from colosseum.config.parameters import (
    ParametersError,
    coerce_bool,
    toml_value_supported,
)
from colosseum.context import RuntimeContext, get_context
from colosseum.runner.runtime import ensure_runtime_ready

if TYPE_CHECKING:
    import types
    from collections.abc import Callable


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
    command: str = "",
) -> tuple[Any, bool]:
    """Return ``(key, injected)`` for a measurement or verification call.

    An explicit key is returned unchanged. Measurements auto-number only when
    ``auto_key()`` is enabled. Verifications always auto-number an omitted key
    (never persist an empty key). The first assignment logs a warning.
    """
    raw = kwargs.get("key")
    if raw:
        return raw, False
    if family == "measurement" and not ctx.auto_key_enabled:
        return None, False
    if family == "measurement":
        ctx.next_measurement_key += 1
        assigned = ctx.next_measurement_key
    else:
        ctx.next_verification_key += 1
        assigned = ctx.next_verification_key
    key = str(assigned)
    kwargs["key"] = key
    if family == "verification" and not ctx.auto_key_enabled:
        if ctx.logger is not None:
            ctx.logger.warning(
                "%s",
                missing_key_guidance(
                    kind="verification",
                    command=command or "verification",
                ),
            )
        return key, True
    if not ctx.auto_key_warned:
        ctx.auto_key_warned = True
        if ctx.logger is not None:
            ctx.logger.warning(
                "col.auto_key() is on; later verifications must use the same numeric keys or an explicit key=",
            )
    return key, True


def missing_key_guidance(*, kind: str, command: str) -> str:
    """Return an actionable message when a decorated call omits ``key=``."""
    if kind == "measurement":
        return (
            f"`{command}` measurement was missing a key; "
            "pass key=... or call col.auto_key() near the start of main()"
        )
    if kind == "verification":
        return (
            f"`{command}` verification omitted key=; "
            "assigned an auto key — prefer an explicit key= or call "
            "col.auto_key() when pairing with measurements"
        )
    return f"`{command}` {kind} was missing a key; pass key=... or call col.auto_key() near the start of main()"


def note_dry_run_tip(ctx: RuntimeContext, message: str) -> None:
    """Record a soft dry-run tip once and mirror it to the run log."""
    if not ctx.run_options.dry_run:
        return
    if message in ctx.dry_run_tips:
        return
    ctx.dry_run_tips.append(message)
    if ctx.logger is not None:
        ctx.logger.warning(message)


def finalize_dry_run_tips(ctx: RuntimeContext) -> None:
    """Add end-of-walk tips (unused parameters, empty walk) before summary write."""
    if not ctx.run_options.dry_run:
        return
    records = ctx.result_aggregator._records  # noqa: SLF001
    evidence_kinds = {"command", "measurement", "verification"}
    if not any(row.get("kind") in evidence_kinds for row in records):
        note_dry_run_tip(
            ctx,
            "dry-run saw no command/measurement/verification calls; check that main() runs and plugins are loaded",
        )
    if ctx.parameters_map:
        unused = sorted(key for key in ctx.parameters_map if key not in ctx.dry_run_keys_seen)
        if unused:
            listed = ", ".join(repr(key) for key in unused)
            note_dry_run_tip(
                ctx,
                f"parameters file has unused section(s): {listed}; check for typos or stale keys",
            )


def _publish_keyword_parameter(
    wrapper: Callable[..., Any],
    func: Callable[..., Any],
    *,
    name: str,
    default: object,
    annotation: object,
) -> None:
    # Prefer an already-published wrapper signature so successive publishes
    # (optional, description, requirements) accumulate instead of replace.
    original = getattr(wrapper, "__signature__", None) or signature(func)
    if name in original.parameters:
        return
    if name in signature(func).parameters:
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
_OUTCOME_STATUSES = frozenset({"PASS", "FAIL", "ERROR", "BLOCKED", "DRY"})
_OUTCOME_STATUS_ALIASES = {
    "PASSED": "PASS",
    "FAILED": "FAIL",
    "FAILURE": "FAIL",
    "OK": "PASS",
}


def normalize_outcome_status(status: str) -> str:
    """Return a canonical outcome status or raise ``ValueError``."""
    text = str(status).strip()
    if not text:
        raise ValueError("outcome status must be non-empty")
    canonical = _OUTCOME_STATUS_ALIASES.get(text.upper(), text.upper())
    if canonical not in _OUTCOME_STATUSES:
        allowed = ", ".join(sorted(_OUTCOME_STATUSES))
        raise ValueError(f"invalid outcome status {status!r}; expected one of: {allowed}")
    return canonical


def bind_dry_run_policy(wrapper: Callable[..., Any], policy: object) -> None:
    """Store ``dry_run`` on a decorator wrapper.

    ``"log"`` skips the body and records the arguments. ``"call"`` runs the body.
    A callable replaces the body during a dry run.
    """
    if policy != "log" and policy != "call" and not callable(policy):
        raise TypeError(
            f"dry_run must be 'log', 'call', or a callable, got {type(policy).__name__}",
        )
    setattr(wrapper, DRY_RUN_ATTR, policy)


def capture_parameter_export(
    ctx: RuntimeContext,
    *,
    kind: str,
    command: str,
    key: str,
    kwargs: dict[str, Any],
) -> bool:
    """Store one keyed call while exporting parameters.

    Returns True when this call should not run. Commands and verifications
    without a key are omitted. A measurement without a key is an export error.
    """
    if ctx.parameter_export is None:
        return False
    if not key:
        if kind == "measurement":
            ctx.export_errors.append(missing_key_guidance(kind=kind, command=command))
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


def optional_from_caller(kwargs: dict[str, Any]) -> bool:
    """Return the caller's ``optional=`` as a bool, or ``False`` when absent or invalid."""
    if "optional" not in kwargs:
        return False
    try:
        return coerce_bool(kwargs["optional"])
    except ParametersError:
        return False


def publish_description_parameter(wrapper: Callable[..., Any], func: Callable[..., Any]) -> None:
    """Expose keyword-only ``description: str = ""`` on a verification wrapper.

    Functions that already declare ``description`` keep their own signature.
    """
    _publish_keyword_parameter(wrapper, func, name="description", default="", annotation=str)


def publish_requirements_parameter(wrapper: Callable[..., Any], func: Callable[..., Any]) -> None:
    """Expose keyword-only ``requirements`` on a verification wrapper.

    Functions that already declare ``requirements`` keep their own signature.
    """
    _publish_keyword_parameter(
        wrapper,
        func,
        name="requirements",
        default="",
        annotation=object,
    )
