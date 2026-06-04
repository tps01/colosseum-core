from __future__ import annotations

from colosseum.config.loader import ConfigError
from colosseum.context import require_context


def _cache_key(kind: str, resource_id: int) -> str:
    return f"io:backend:{kind}:{resource_id}"


def get_config(kind: str, resource_id: int) -> dict:
    ctx = require_context()
    if ctx.config is None:
        raise ConfigError("Configuration is not loaded. Call col.config.load_config(path).")
    return ctx.config.require_item(f"io.{kind}", resource_id)


def get_backend(kind: str, resource_id: int):
    ctx = require_context()
    key = _cache_key(kind, resource_id)
    if key not in ctx.resource_cache:
        from colosseum_equipment.io.backends.factory import open_backend

        cfg = get_config(kind, resource_id)
        ctx.resource_cache[key] = open_backend(kind, resource_id, cfg)
    return ctx.resource_cache[key]
