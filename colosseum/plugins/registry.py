from __future__ import annotations

import logging
import types
from collections import defaultdict
from typing import Callable, Iterable, List, Optional

from ..config.sections import ConfigSectionSpec

_logger = logging.getLogger("colosseum.plugins")


class PluginRegistry:
    def __init__(self) -> None:
        self._sections: dict[str, ConfigSectionSpec] = {}
        self._validators: dict[str, list[Callable[[dict], list[str]]]] = defaultdict(list)
        self._namespaces: dict[str, types.ModuleType] = {}
        self._shutdown_hooks: list[Callable[[], None]] = []
        self._loaded = False

    def register_config_section(self, spec: ConfigSectionSpec) -> None:
        if spec.dotted_path in self._sections:
            _logger.warning("Replacing config section spec for `%s`", spec.dotted_path)
        self._sections[spec.dotted_path] = spec

    def register_config_validator(self, dotted_path: str, validator: Callable[[dict], list[str]]) -> None:
        self._validators[dotted_path].append(validator)

    def register_namespace(self, name: str, module: types.ModuleType) -> None:
        if name in self._namespaces:
            _logger.warning("Replacing namespace `%s` from plugin registration", name)
        self._namespaces[name] = module

    def register_shutdown(self, hook: Callable[[], None]) -> None:
        self._shutdown_hooks.append(hook)

    def config_section_specs(self) -> list[ConfigSectionSpec]:
        return list(self._sections.values())

    def iter_config_sections(self) -> Iterable[ConfigSectionSpec]:
        return self.config_section_specs()

    def validators_for(self, dotted_path: str) -> list[Callable[[dict], list[str]]]:
        return self._validators.get(dotted_path, [])

    def get_namespace(self, name: str) -> types.ModuleType:
        if name not in self._namespaces:
            raise RuntimeError(
                f"Namespace `{name}` is not registered. Install the plugin package "
                f"(e.g. colosseum-{name}) and ensure it exposes a colosseum.plugins entry point."
            )
        return self._namespaces[name]

    def has_namespace(self, name: str) -> bool:
        return name in self._namespaces

    def run_shutdown(self) -> None:
        for hook in reversed(self._shutdown_hooks):
            try:
                hook()
            except Exception:
                _logger.exception("Plugin shutdown hook failed")

    @property
    def loaded(self) -> bool:
        return self._loaded

    @loaded.setter
    def loaded(self, value: bool) -> None:
        self._loaded = value
