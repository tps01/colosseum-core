from __future__ import annotations

import atexit
import logging

from colosseum.context import get_context, require_context

from colosseum_equipment.transports.base import Transport

_logger = logging.getLogger("colosseum.equipment")
_atexit_registered = False


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
    keys = [
        k
        for k in list(ctx.resource_cache)
        if k.startswith("equipment:")
        or k.startswith("instrument:")
        or k.startswith("io:backend:")
    ]
    instrument_keys = [k for k in keys if k.startswith("instrument:")]
    io_keys = [k for k in keys if k.startswith("io:backend:")]
    equipment_keys = [k for k in keys if k.startswith("equipment:")]
    for key in instrument_keys + io_keys + equipment_keys:
        resource = ctx.resource_cache.pop(key, None)
        close = getattr(resource, "close", None)
        if not callable(close):
            continue
        try:
            close()
        except Exception:
            _logger.exception("Failed to close cached resource %s", key)


def _atexit_close_equipment() -> None:
    ctx = get_context()
    if ctx is None or ctx.finalized:
        return
    try:
        close_all()
    except Exception:
        _logger.exception("atexit equipment close failed")


def register_atexit_cleanup() -> None:
    global _atexit_registered
    if _atexit_registered:
        return
    atexit.register(_atexit_close_equipment)
    _atexit_registered = True
