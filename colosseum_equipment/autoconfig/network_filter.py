"""Blacklist resolution and TCPIP resource filtering for autoconfig."""

from __future__ import annotations

import ipaddress
from collections.abc import Sequence
from dataclasses import dataclass

from colosseum_shared.network import (
    IPv4NetworkBinding,
    bindings_for_blacklist_entry,
    list_ipv4_network_bindings,
)

from .sort import is_tcpip_resource, parse_tcpip_host_ip


@dataclass(frozen=True)
class BlockedSubnet:
    """A subnet excluded from TCPIP autoconfig probing."""

    interface: str
    address: str
    network: ipaddress.IPv4Network
    label: str


@dataclass(frozen=True)
class BlacklistResolution:
    """Outcome of resolving ``blacklist`` entries."""

    blocked: tuple[BlockedSubnet, ...]
    unresolved_entries: tuple[str, ...]


def resolve_blacklist(
    blacklist: str | Sequence[str] | None,
    *,
    bindings: Sequence[IPv4NetworkBinding] | None = None,
) -> BlacklistResolution:
    """Resolve blacklist entries to blocked IPv4 subnets."""
    if blacklist is None:
        return BlacklistResolution(blocked=(), unresolved_entries=())
    entries = [blacklist] if isinstance(blacklist, str) else list(blacklist)
    local_bindings = list(bindings) if bindings is not None else list_ipv4_network_bindings()
    blocked: list[BlockedSubnet] = []
    unresolved: list[str] = []
    seen: set[tuple[str, int]] = set()
    for entry in entries:
        matches = bindings_for_blacklist_entry(entry, local_bindings)
        if not matches:
            unresolved.append(entry)
            continue
        for binding in matches:
            network = ipaddress.IPv4Network(f"{binding.network}/{binding.prefix}", strict=False)
            key = (str(network.network_address), network.prefixlen)
            if key in seen:
                continue
            seen.add(key)
            blocked.append(
                BlockedSubnet(
                    interface=binding.interface,
                    address=binding.address,
                    network=network,
                    label=entry,
                )
            )
    return BlacklistResolution(blocked=tuple(blocked), unresolved_entries=tuple(unresolved))


def is_resource_blacklisted(
    resource: str,
    blocked: Sequence[BlockedSubnet],
) -> BlockedSubnet | None:
    """Return the matching blocked subnet when ``resource`` is a blacklisted TCPIP entry."""
    if not blocked or not is_tcpip_resource(resource):
        return None
    host_ip = parse_tcpip_host_ip(resource)
    if host_ip is None:
        return None
    for subnet in blocked:
        if host_ip in subnet.network:
            return subnet
    return None


def filter_resources(
    resources: list[str],
    blocked: Sequence[BlockedSubnet],
) -> tuple[list[str], list[tuple[str, BlockedSubnet]]]:
    """Split ``resources`` into allowed list and blacklisted (resource, subnet) pairs."""
    allowed: list[str] = []
    dropped: list[tuple[str, BlockedSubnet]] = []
    for resource in resources:
        match = is_resource_blacklisted(resource, blocked)
        if match is None:
            allowed.append(resource)
        else:
            dropped.append((resource, match))
    return allowed, dropped
