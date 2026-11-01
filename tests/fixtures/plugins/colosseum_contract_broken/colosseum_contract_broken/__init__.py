"""Broken plugin: register raises so core must fail fast."""

from __future__ import annotations

from colosseum.plugins.registry import PluginRegistry


def register(registry: PluginRegistry) -> None:
    _ = registry
    raise RuntimeError("contract broken on purpose")
