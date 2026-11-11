"""Shared control flow for command, measurement, and verification decorators."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from colosseum.units import coerce_units

from ._common import ensure_runtime_context
from ._dry_run import finish_dry_run_log, invoke_dry_run_substitute

if TYPE_CHECKING:
    from colosseum.context import RuntimeContext

    from .command import _CommandBinding
    from .measurement import _MeasurementBinding
    from .verification import _VerificationBinding


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


def run_decorated_call(
    binding: _CommandBinding | _MeasurementBinding | _VerificationBinding,
    *args: Any,  # noqa: ANN401
    **kwargs: Any,  # noqa: ANN401
) -> Any:  # noqa: ANN401
    """Run the shared decorator pipeline for one evidence kind."""
    ctx = ensure_runtime_context()
    if binding.should_skip(ctx):
        return None
    identity = binding.resolve_identity(ctx, kwargs)
    early = _run_before_dry_run(binding, ctx, identity, args, kwargs)
    if early is not None:
        return early.value
    if finish_dry_run_log(ctx, **binding.dry_run_fields(identity, args, kwargs)):
        return None
    if binding.kind == "measurement":
        binding.after_dry_run(ctx, identity, kwargs)
    prepared = binding.prepare(ctx, identity, args, kwargs)
    if isinstance(prepared, EarlyReturn):
        return prepared.value
    handled, value = invoke_dry_run_substitute(
        ctx,
        kind=binding.kind,
        domain=binding.domain,
        command=binding.command,
        key=identity.key_text,
        optional=prepared.optional,
        policy=binding.dry_run,
        call_args=args,
        call_kwargs=prepared.call_kwargs,
        logged_kwargs=prepared.logged_kwargs,
        description=prepared.description,
        requirements=prepared.requirements,
    )
    if handled:
        return value
    return _invoke_body(binding, ctx, identity, prepared, args)


def _run_before_dry_run(
    binding: _CommandBinding | _MeasurementBinding | _VerificationBinding,
    ctx: RuntimeContext,
    identity: Identity,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> EarlyReturn | None:
    if binding.kind == "measurement":
        return binding.before_dry_run(ctx, identity, args, kwargs)
    return None


def _invoke_body(
    binding: _CommandBinding | _MeasurementBinding | _VerificationBinding,
    ctx: RuntimeContext,
    identity: Identity,
    prepared: PreparedCall,
    args: tuple[Any, ...],
) -> Any:  # noqa: ANN401
    try:
        prepared.call_kwargs = coerce_units(prepared.call_kwargs)
        value = binding.func(*args, **prepared.call_kwargs)
        return binding.persist_success(ctx, identity, prepared, value)
    except Exception as exc:  # noqa: BLE001
        return binding.persist_error(ctx, identity, prepared, exc)
