from __future__ import annotations

from colosseum.context import require_context

from colosseum_shared.ssh.client import SSHClientWrapper


def get_ssh_client(ssh_id: int) -> SSHClientWrapper:
    ctx = require_context()
    key = f"shared:ssh:{ssh_id}"
    if key not in ctx.resource_cache:
        cfg = ctx.config.require_item("shared.ssh", ssh_id)
        ctx.resource_cache[key] = SSHClientWrapper(cfg)
    return ctx.resource_cache[key]


def close_all() -> None:
    ctx = require_context()
    keys = [k for k in ctx.resource_cache if k.startswith("shared:ssh:")]
    for key in keys:
        client = ctx.resource_cache.pop(key, None)
        close = getattr(client, "close", None)
        if callable(close):
            close()
