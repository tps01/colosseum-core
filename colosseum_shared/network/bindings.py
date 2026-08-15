"""Platform dispatch for local IPv4 interface/network lookup."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class IPv4NetworkBinding:
    """Local IPv4 address and subnet on a named interface."""

    interface: str
    address: str
    network: str
    prefix: int


def list_ipv4_network_bindings() -> list[IPv4NetworkBinding]:
    """Return IPv4 address/subnet bindings for local network interfaces."""
    if sys.platform.startswith("win"):
        from . import windows as platform_module
    elif sys.platform.startswith("linux"):
        from . import linux as platform_module
    else:
        return []
    return platform_module.list_ipv4_network_bindings()


def bindings_for_blacklist_entry(
    entry: str, bindings: Sequence[IPv4NetworkBinding]
) -> list[IPv4NetworkBinding]:
    """Resolve a blacklist entry (interface name or local IPv4) to matching bindings."""
    entry = entry.strip()
    if not entry:
        return []
    lowered = entry.lower()
    for binding in bindings:
        if binding.address.lower() == lowered:
            return [binding]
    matches = [binding for binding in bindings if binding.interface.lower() == lowered]
    if matches:
        return matches
    return []
