"""Config and resource helpers — TODO: implement when your extension needs them."""

from __future__ import annotations

from typing import Any

from colosseum.logging import get_logger

_logger = get_logger("colosseum.template")


def get_config(device_id: int) -> dict[str, Any]:
    """TODO: Load ``template.device`` row from bench config.

    Example::

        from colosseum.config.loader import ConfigError
        from colosseum.context import require_context

        ctx = require_context()
        if ctx.config is None:
            raise ConfigError("Configuration is not loaded.")
        row = ctx.config.require_item("template.device", device_id)
        _logger.debug("Loaded template.device id=%s", device_id)
        return row
    """
    raise NotImplementedError("TODO: implement get_config() for template.device")


def close_all() -> None:
    """TODO: Close cached transports/instruments (register via register_shutdown)."""
    _logger.debug("close_all: releasing template resources")
    # Your code here.
