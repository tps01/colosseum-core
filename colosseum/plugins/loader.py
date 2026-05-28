from __future__ import annotations

import importlib
import logging

from colosseum.compat.entry_points import entry_points_for_group

from .registry import PluginRegistry

_logger = logging.getLogger("colosseum.plugins")

# Monorepo fallback when running from source without installed entry-point metadata.
_BUILTIN_PLUGINS = (
    ("equipment", "colosseum_equipment", "register"),
    ("shared", "colosseum_shared", "register"),
)


def _load_builtin_plugins(registry: PluginRegistry) -> None:
    for name, module_name, attr in _BUILTIN_PLUGINS:
        try:
            module = importlib.import_module(module_name)
            getattr(module, attr)(registry)
        except Exception:
            _logger.exception("Failed to load built-in plugin `%s`", name)


def ensure_plugins_loaded(registry: PluginRegistry) -> None:
    if registry.loaded:
        return

    eps = entry_points_for_group("colosseum.plugins")
    if eps:
        for ep in eps:
            try:
                plugin_register = ep.load()
                plugin_register(registry)
            except Exception:
                _logger.exception("Failed to load plugin entry point `%s`", ep.name)
    else:
        _load_builtin_plugins(registry)

    registry.loaded = True
