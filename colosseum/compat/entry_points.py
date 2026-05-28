from __future__ import annotations

from typing import List

try:
    from importlib.metadata import entry_points
except ImportError:  # pragma: no cover
    from importlib_metadata import entry_points  # type: ignore


def entry_points_for_group(group: str) -> List[object]:
    """Return entry points for *group* on Python 3.9 and 3.10+."""
    discovered = entry_points()
    select = getattr(discovered, "select", None)
    if select is not None:
        return list(select(group=group))
    get = getattr(discovered, "get", None)
    if get is not None:
        return list(get(group, []))
    return [ep for ep in discovered if getattr(ep, "group", None) == group]
