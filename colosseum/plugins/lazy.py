"""Defer importing a plugin API module until an attribute is first accessed."""

from __future__ import annotations

import importlib
import types
from typing import Any


class LazyModuleProxy(types.ModuleType):
    """Module stand-in that imports ``target`` on first attribute access."""

    def __init__(self, name: str, target: str) -> None:
        super().__init__(name)
        object.__setattr__(self, "_colosseum_lazy_target", target)
        object.__setattr__(self, "_colosseum_lazy_module", None)

    def _load(self) -> types.ModuleType:
        loaded = object.__getattribute__(self, "_colosseum_lazy_module")
        if isinstance(loaded, types.ModuleType):
            return loaded
        target = object.__getattribute__(self, "_colosseum_lazy_target")
        module = importlib.import_module(str(target))
        if not isinstance(module, types.ModuleType):  # pragma: no cover
            raise TypeError(f"expected module for {target!r}, got {type(module)!r}")
        object.__setattr__(self, "_colosseum_lazy_module", module)
        return module

    def __getattr__(self, item: str) -> Any:  # noqa: ANN401
        return getattr(self._load(), item)

    def __setattr__(self, key: str, value: object) -> None:
        if key.startswith("_colosseum_lazy_") or key == "__colosseum_domain__":
            object.__setattr__(self, key, value)
            return
        setattr(self._load(), key, value)

    def __dir__(self) -> list[str]:
        return dir(self._load())


def lazy_module(target: str, *, name: str | None = None) -> types.ModuleType:
    """Return a proxy that imports ``target`` when first used."""
    return LazyModuleProxy(name or target, target)
