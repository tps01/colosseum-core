from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, cast

try:
    from importlib.metadata import entry_points
except ImportError:  # pragma: no cover
    from importlib_metadata import entry_points  # type: ignore[import-not-found,no-redef]


class ColosseumPluginEntryPoint(Protocol):
    @property
    def name(self) -> str: ...

    def load(self) -> Callable[..., object]: ...


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


def entry_points_for_group(group: str) -> list[ColosseumPluginEntryPoint]:
    """Return entry points for *group* (importlib.metadata compat shim).

    :param group: Entry-point group name (for example ``colosseum.plugins``).
    :type group: str

    :returns: Discovered entry points for the group (empty when none are installed).
    :rtype: list[ColosseumPluginEntryPoint]
    """
    return _discovered_for_group(group)
