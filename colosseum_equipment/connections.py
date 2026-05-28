from __future__ import annotations

from colosseum.context import require_context

from colosseum_equipment.transports.base import Transport


def _cache_key(kind: str, equipment_id: int) -> str:
    return f"equipment:{kind}:{equipment_id}"


def get_config(kind: str, equipment_id: int) -> dict:
    ctx = require_context()
    return ctx.config.require_item(f"equipment.{kind}", equipment_id)


def get_transport(kind: str, equipment_id: int) -> Transport:
    ctx = require_context()
    key = _cache_key(kind, equipment_id)
    if key not in ctx.resource_cache:
        from colosseum_equipment.transports.factory import open_transport

        cfg = get_config(kind, equipment_id)
        ctx.resource_cache[key] = open_transport(kind, equipment_id, cfg)
    return ctx.resource_cache[key]


def get_cached_instrument(kind: str, equipment_id: int):
    ctx = require_context()
    key = f"instrument:{kind}:{equipment_id}"
    if key not in ctx.resource_cache:
        from colosseum_equipment.instruments.factory import build_instrument

        cfg = get_config(kind, equipment_id)
        transport = get_transport(kind, equipment_id)
        ctx.resource_cache[key] = build_instrument(kind, equipment_id, cfg, transport)
    return ctx.resource_cache[key]


def close_all() -> None:
    ctx = require_context()
    keys = [k for k in list(ctx.resource_cache) if k.startswith("equipment:") or k.startswith("instrument:")]
    for key in keys:
        resource = ctx.resource_cache.pop(key, None)
        close = getattr(resource, "close", None)
        if callable(close):
            close()
