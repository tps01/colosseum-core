from __future__ import annotations

import importlib

from colosseum.compat.entry_points import entry_points_for_group
from colosseum.logging import get_logger

from .registry import PluginRegistrationError, PluginRegistry

_logger = get_logger("colosseum.plugins")

# Monorepo fallback when running from source without installed entry-point metadata.
_BUILTIN_PLUGINS = (
    ("equipment", "colosseum_equipment", "register"),
    ("shared", "colosseum_shared", "register"),
    ("host", "colosseum_host", "register"),
)
_BUILTIN_PLUGIN_NAMES = {name for name, _module_name, _attr in _BUILTIN_PLUGINS}


def _load_builtin_plugins(registry: PluginRegistry) -> None:
    for name, module_name, attr in _BUILTIN_PLUGINS:
        try:
            module = importlib.import_module(module_name)
            getattr(module, attr)(registry)
            _logger.debug("Loaded built-in plugin: %s", name)
        except PluginRegistrationError:
            raise
        except Exception:
            _logger.exception("Failed to load built-in plugin `%s`", name)


def ensure_plugins_loaded(registry: PluginRegistry) -> None:
    if registry.loaded:
        return

    _load_builtin_plugins(registry)
    eps = entry_points_for_group("colosseum.plugins")
    for ep in eps:
        if ep.name in _BUILTIN_PLUGIN_NAMES:
            _logger.debug("Skipping built-in plugin entry point already loaded: %s", ep.name)
            continue
        try:
            plugin_register = ep.load()
            plugin_register(registry)
            _logger.debug("Loaded plugin entry point: %s", ep.name)
        except PluginRegistrationError:
            raise
        except Exception:
            _logger.exception("Failed to load plugin entry point `%s`", ep.name)

    registry.loaded = True
    _logger.debug(
        "Plugin registry ready: %d config section(s)",
        len(registry.config_section_specs()),
    )
