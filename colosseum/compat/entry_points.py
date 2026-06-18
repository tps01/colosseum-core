from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, cast

try:
    from importlib.metadata import entry_points
except ImportError:  # pragma: no cover
    from importlib_metadata import entry_points  # type: ignore[import-not-found,no-redef]


class ColosseumPluginEntryPoint(Protocol):
    name: str

    def load(self) -> Callable[..., None]: ...


def entry_points_for_group(group: str) -> list[ColosseumPluginEntryPoint]:
    """Return entry points for *group* (importlib.metadata compat shim)."""
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
