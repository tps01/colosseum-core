"""Public API for ``col.contract_probe`` (fixture plugin)."""

from __future__ import annotations

from colosseum.decorators import command, measurement


@command
def ping() -> str:
    """Return a fixed token so e2e can assert namespace attachment."""
    return "pong"


@command
def arm_device(*, device_id: int) -> str:
    """Read a configured device row and return its serial."""
    from colosseum.config.loader import ConfigError
    from colosseum.context import get_context

    ctx = get_context()
    if ctx.config is None:
        raise ConfigError("Configuration is not loaded.")
    row = ctx.config.require_item("contract_probe.device", device_id)
    return str(row["serial"])


@measurement
def measure_token(*, key: str) -> str:
    """Record a simple measurement for evidence-domain checks."""
    return "token-ok"
