from __future__ import annotations

import logging
from typing import Any

from colosseum.config.loader import ConfigError
from colosseum.context import require_context
from colosseum.resource_cache import cached_resource, close_cached_resources

_logger = logging.getLogger("colosseum.io")


def _cache_key(kind: str, resource_id: int) -> str:
    return f"io:backend:{kind}:{resource_id}"


def get_config(kind: str, resource_id: int) -> dict[str, Any]:
    ctx = require_context()
    if ctx.config is None:
        raise ConfigError("Configuration is not loaded. Call col.config.load_config(path).")
    return ctx.config.require_item(f"io.{kind}", resource_id)


def get_backend(kind: str, resource_id: int) -> Any:  # noqa: ANN401
    ctx = require_context()
    key = _cache_key(kind, resource_id)
    cfg = get_config(kind, resource_id)
    driver = str(cfg.get("driver") or "stub").lower()

    def _open() -> Any:  # noqa: ANN401
        from colosseum_equipment.io.backends.factory import open_backend

        return open_backend(kind, resource_id, cfg)

    return cached_resource(
        ctx.resource_cache,
        key,
        _open,
        on_reuse=lambda: _logger.debug("Reusing cached io backend io.%s id=%s", kind, resource_id),
        on_open=lambda: _logger.debug(
            "Opening io backend io.%s id=%s driver=%s", kind, resource_id, driver
        ),
    )


def close_all() -> None:
    ctx = require_context()
    close_cached_resources(ctx.resource_cache, (("io:backend:",),), logger=_logger)
