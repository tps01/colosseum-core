from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast

try:
    from importlib.metadata import entry_points
except ImportError:  # pragma: no cover
    from importlib_metadata import entry_points  # type: ignore[import-not-found,no-redef]


class ColosseumPluginEntryPoint(Protocol):
    name: str

    def load(self) -> Callable[..., object]: ...


# Monorepo fallback when running from source without installed entry-point metadata.
_FALLBACK_ENTRY_POINTS: dict[str, dict[str, str]] = {
    "colosseum.plugins": {
        "equipment": "colosseum_equipment:register",
        "shared": "colosseum_shared:register",
        "host": "colosseum_host:register",
    },
    "colosseum.docgen": {
        "colosseum": "colosseum.docgen_entry:spec",
        "equipment": "colosseum_equipment.docgen_entry:spec",
        "shared": "colosseum_shared.docgen_entry:spec",
        "host": "colosseum_host.docgen_entry:spec",
    },
}


@dataclass(frozen=True)
class _FallbackEntryPoint:
    name: str
    target: str

    def load(self) -> Callable[..., object]:
        module_name, attr = self.target.split(":", 1)
        module = importlib.import_module(module_name)
        return getattr(module, attr)


def _discovered_for_group(group: str) -> list[ColosseumPluginEntryPoint]:
    discovered = entry_points()
    select = getattr(discovered, "select", None)
    if select is not None:
        return cast(list[ColosseumPluginEntryPoint], list(select(group=group)))
    get = getattr(discovered, "get", None)
    if get is not None:
        return cast(list[ColosseumPluginEntryPoint], list(get(group, [])))
    return cast(
        list[ColosseumPluginEntryPoint],
        [ep for ep in discovered if getattr(ep, "group", None) == group],
    )


def _fallback_for_group(group: str) -> list[ColosseumPluginEntryPoint]:
    targets = _FALLBACK_ENTRY_POINTS.get(group)
    if targets is None:
        return []
    return [
        _FallbackEntryPoint(name=name, target=target)
        for name, target in sorted(targets.items())
    ]


def entry_points_for_group(group: str) -> list[ColosseumPluginEntryPoint]:
    """Return entry points for *group* (importlib.metadata compat shim).

    When package metadata is unavailable (source checkout without ``pip install -e .``),
    built-in monorepo entry points are synthesized to match ``pyproject.toml``.
    """
    eps = _discovered_for_group(group)
    if eps:
        return eps
    return _fallback_for_group(group)
