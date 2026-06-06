from __future__ import annotations

import logging

from colosseum.config.loader import ConfigError
from colosseum.context import require_context
from colosseum.resource_cache import cached_resource, close_cached_resources

from colosseum_shared.ssh.client import SSHClientWrapper

_logger = logging.getLogger("colosseum.shared")


def get_ssh_client(ssh_id: int) -> SSHClientWrapper:
    ctx = require_context()
    key = f"shared:ssh:{ssh_id}"
    if ctx.config is None:
        raise ConfigError("Configuration is not loaded. Call col.config.load_config(path).")
    cfg = ctx.config.require_item("shared.ssh", ssh_id)
    driver = str(cfg.get("driver", "ssh")).lower()

    def _open() -> SSHClientWrapper:
        return SSHClientWrapper(cfg)

    return cached_resource(
        ctx.resource_cache,
        key,
        _open,
        on_reuse=lambda: _logger.debug("Reusing cached SSH client shared.ssh id=%s", ssh_id),
        on_open=lambda: _logger.debug(
            "Opening SSH client shared.ssh id=%s driver=%s host=%s",
            ssh_id,
            driver,
            cfg.get("host"),
        ),
    )


def close_all() -> None:
    ctx = require_context()
    close_cached_resources(ctx.resource_cache, (("shared:ssh:",),), logger=_logger)
