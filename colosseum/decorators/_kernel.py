"""Shared evidence decorator helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from colosseum.context import RuntimeContext

_REDACT_KEYS = frozenset({"password", "passwd", "token", "secret", "api_key"})


def short_repr(value: object, *, limit: int = 120) -> str:
    text = repr(value)
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def redact_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for name, value in kwargs.items():
        if name.lower() in _REDACT_KEYS:
            redacted[name] = "***"
        else:
            redacted[name] = value
    return redacted


def call_args_text(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    """Format a call's arguments without truncating values."""
    redacted = redact_kwargs(kwargs)
    if args:
        return f"args={args!r} kwargs={redacted!r}"
    return f"args={redacted!r}"


def log_evidence(
    ctx: RuntimeContext,
    *,
    kind: str,
    domain: str,
    command: str,
    key: str,
    status: str,
    optional: bool = False,
    detail: str = "",
    call_args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
) -> None:
    if ctx.logger is None:
        return
    parts: list[str] = []
    if kwargs is not None or call_args:
        parts.append(call_args_text(call_args, kwargs or {}))
    if detail:
        parts.append(detail)
    if parts:
        ctx.logger.debug("%s %s.%s key=%s %s", kind, domain, command, key, " ".join(parts))
    ctx.logger.info(
        "%s %s.%s key=%s status=%s optional=%s",
        kind,
        domain,
        command,
        key,
        status,
        optional,
    )


def log_evidence_error(
    ctx: RuntimeContext,
    *,
    kind: str,
    domain: str,
    command: str,
    key: str,
    cause: str = "",
    call_args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
) -> None:
    if ctx.logger is None:
        return
    args_text = ""
    if kwargs is not None or call_args:
        args_text = " " + call_args_text(call_args, kwargs or {})
    cause_text = f" cause={cause}" if cause else ""
    ctx.logger.exception(
        "%s %s.%s key=%s status=ERROR%s%s",
        kind,
        domain,
        command,
        key,
        cause_text,
        args_text,
    )


def record_error_event(ctx: RuntimeContext, *, domain: str, command: str, exc: Exception) -> None:
    ctx.db.insert_event("ERROR", f"{domain}.{command}", str(exc))
