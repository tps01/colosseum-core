from __future__ import annotations

import atexit
import logging
from typing import Any

from colosseum.config.loader import ConfigError
from colosseum.context import get_context, require_context
from colosseum.resource_cache import cached_resource, close_cached_resources

from colosseum_equipment.transports.base import Transport

_logger = logging.getLogger("colosseum.equipment")
_atexit_registered = False


def _cache_key(kind: str, equipment_id: int) -> str:
    return f"equipment:{kind}:{equipment_id}"


def get_config(kind: str, equipment_id: int) -> dict[str, Any]:
    ctx = require_context()
    if ctx.config is None:
        raise ConfigError("Configuration is not loaded. Call col.config.load_config(path).")
    return ctx.config.require_item(f"equipment.{kind}", equipment_id)


def get_transport(kind: str, equipment_id: int) -> Transport:
    ctx = require_context()
    key = _cache_key(kind, equipment_id)
    cfg = get_config(kind, equipment_id)
    driver = str(cfg.get("driver", "visa")).lower()

    def _open() -> Transport:
        from colosseum_equipment.transports.factory import open_transport

        return open_transport(kind, equipment_id, cfg)

    return cached_resource(
        ctx.resource_cache,
        key,
        _open,
        on_reuse=lambda: _logger.debug(
            "Reusing cached transport equipment.%s id=%s", kind, equipment_id
        ),
        on_open=lambda: _logger.debug(
            "Opening transport equipment.%s id=%s driver=%s", kind, equipment_id, driver
        ),
    )


def get_cached_instrument(kind: str, equipment_id: int) -> Any:  # noqa: ANN401
    ctx = require_context()
    key = f"instrument:{kind}:{equipment_id}"
    cfg = get_config(kind, equipment_id)
    model = str(cfg.get("model", "generic")).lower()

    def _open() -> Any:  # noqa: ANN401
        from colosseum_equipment.instruments.factory import build_instrument

        transport = get_transport(kind, equipment_id)
        return build_instrument(kind, equipment_id, cfg, transport)

    return cached_resource(
        ctx.resource_cache,
        key,
        _open,
        on_reuse=lambda: _logger.debug(
            "Reusing cached instrument equipment.%s id=%s", kind, equipment_id
        ),
        on_open=lambda: _logger.debug(
            "Building instrument equipment.%s id=%s model=%s", kind, equipment_id, model
        ),
    )


def close_all() -> None:
    ctx = require_context()
    close_cached_resources(ctx.resource_cache, (("instrument:",),), logger=_logger)
    from colosseum_equipment.io.connections import close_all as close_io_backends

    close_io_backends()
    close_cached_resources(ctx.resource_cache, (("equipment:",),), logger=_logger)


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
