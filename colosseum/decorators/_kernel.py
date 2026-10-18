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
) -> None:
    if ctx.logger is None:
        return
    if detail:
        ctx.logger.debug("%s %s.%s key=%s %s", kind, domain, command, key, detail)
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
    kwargs: dict[str, Any] | None = None,
) -> None:
    if ctx.logger is None:
        return
    args_text = ""
    if kwargs is not None:
        args_text = f" args={short_repr(redact_kwargs(kwargs))}"
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
