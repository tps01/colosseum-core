"""Shared control flow for command, measurement, and verification decorators."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from colosseum.units import coerce_units

from ._common import capture_parameter_export, ensure_runtime_context
from ._dry_run import finish_dry_run_log, invoke_dry_run_substitute

if TYPE_CHECKING:
    from collections.abc import Callable

    from colosseum.context import RuntimeContext

DecoratorKind = Literal["command", "measurement", "verification"]


@dataclass
class Identity:
    """Resolved evidence identity for one decorated call."""

    key: Any
    key_text: str
    injected: bool = False
    row_index: int = 0


@dataclass
class EarlyReturn:
    """Stop the pipeline and return ``value`` to the caller."""

    value: Any


@dataclass
class PreparedCall:
    """Arguments ready for dry-run substitute or the live body."""

    optional: bool
    call_kwargs: dict[str, Any]
    logged_kwargs: dict[str, Any]
    call_args: tuple[Any, ...] = ()
    description: str = ""
    requirements: list[str] = field(default_factory=list)
    row_index: int = 0


@dataclass
class DecoratorSpec:
    """Kind-specific hooks for :func:`run_decorated_call`."""

    kind: DecoratorKind
    domain: str
    command: str
    func: Callable[..., Any]
    dry_run: object
    should_skip: Callable[[RuntimeContext], bool]
    resolve_identity: Callable[[RuntimeContext, dict[str, Any]], Identity]
    dry_run_fields: Callable[[Identity, tuple[Any, ...], dict[str, Any]], dict[str, Any]]
    prepare: Callable[
        [RuntimeContext, Identity, tuple[Any, ...], dict[str, Any]],
        PreparedCall | EarlyReturn,
    ]
    persist_success: Callable[
        [RuntimeContext, Identity, PreparedCall, object],
        object,
    ]
    persist_error: Callable[
        [RuntimeContext, Identity, PreparedCall, Exception],
        object,
    ]
    before_dry_run: (
        Callable[
            [RuntimeContext, Identity, tuple[Any, ...], dict[str, Any]],
            EarlyReturn | None,
        ]
        | None
    ) = None
    after_dry_run: Callable[[RuntimeContext, Identity, dict[str, Any]], None] | None = None


def run_decorated_call(spec: DecoratorSpec, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
    """Run the shared decorator pipeline for one evidence kind."""
    ctx = ensure_runtime_context()
    if spec.should_skip(ctx):
        return None
    identity = spec.resolve_identity(ctx, kwargs)
    if capture_parameter_export(
        ctx,
        kind=spec.kind,
        command=spec.command,
        key=identity.key_text,
        kwargs=kwargs,
    ):
        return None
    early = _run_before_dry_run(spec, ctx, identity, args, kwargs)
    if early is not None:
        return early.value
    if finish_dry_run_log(ctx, **spec.dry_run_fields(identity, args, kwargs)):
        return None
    if spec.after_dry_run is not None:
        spec.after_dry_run(ctx, identity, kwargs)
    prepared = spec.prepare(ctx, identity, args, kwargs)
    if isinstance(prepared, EarlyReturn):
        return prepared.value
    handled, value = invoke_dry_run_substitute(
        ctx,
        kind=spec.kind,
        domain=spec.domain,
        command=spec.command,
        key=identity.key_text,
        optional=prepared.optional,
        policy=spec.dry_run,
        call_args=args,
        call_kwargs=prepared.call_kwargs,
        logged_kwargs=prepared.logged_kwargs,
        description=prepared.description,
        requirements=prepared.requirements,
    )
    if handled:
        return value
    return _invoke_body(spec, ctx, identity, prepared, args)


def _run_before_dry_run(
    spec: DecoratorSpec,
    ctx: RuntimeContext,
    identity: Identity,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> EarlyReturn | None:
    if spec.before_dry_run is None:
        return None
    return spec.before_dry_run(ctx, identity, args, kwargs)


def _invoke_body(
    spec: DecoratorSpec,
    ctx: RuntimeContext,
    identity: Identity,
    prepared: PreparedCall,
    args: tuple[Any, ...],
) -> Any:  # noqa: ANN401
    try:
        prepared.call_kwargs = coerce_units(prepared.call_kwargs)
        value = spec.func(*args, **prepared.call_kwargs)
        return spec.persist_success(ctx, identity, prepared, value)
    except Exception as exc:  # noqa: BLE001
        return spec.persist_error(ctx, identity, prepared, exc)
