"""VISA resource parse and deterministic sort keys for autoconfig."""

from __future__ import annotations

import ipaddress
import re
from typing import Any

# Lower rank = earlier ID assignment within a kind.
_INTERFACE_RANK: dict[str, int] = {
    "TCPIP": 0,
    "USB": 1,
    "GPIB": 2,
    "ASRL": 3,
    "PXI": 4,
}

_USB_RE = re.compile(r"^USB(\d+)::0x([0-9A-Fa-f]+)::0x([0-9A-Fa-f]+)(?:::([^:]+))?", re.IGNORECASE)
_GPIB_RE = re.compile(r"^GPIB(\d+)::(\d+)", re.IGNORECASE)
_ASRL_RE = re.compile(r"^ASRL(\d+)", re.IGNORECASE)
_PXI_RE = re.compile(r"^PXI(\d+)", re.IGNORECASE)


def interface_name(resource: str) -> str:
    """Return the VISA interface prefix (for example ``TCPIP``, ``GPIB``)."""
    return resource.split("::", 1)[0].upper().split("0")[0] or resource.split("::", 1)[0].upper()


def is_tcpip_resource(resource: str) -> bool:
    """Return True when ``resource`` uses a TCPIP-style VISA interface."""
    prefix = resource.split("::", 1)[0].upper()
    return prefix.startswith("TCPIP")


def parse_tcpip_host_ip(resource: str) -> ipaddress.IPv4Address | None:
    """Extract the instrument IPv4 address from a TCPIP VISA resource string."""
    if not is_tcpip_resource(resource):
        return None
    parts = resource.split("::")
    if len(parts) < 2:
        return None
    host = parts[1]
    try:
        return ipaddress.IPv4Address(host)
    except ipaddress.AddressValueError:
        return None


def _interface_rank(resource: str) -> int:
    name = interface_name(resource)
    return _INTERFACE_RANK.get(name, 99)


def _address_sort_key(resource: str) -> tuple[Any, ...]:
    upper = resource.upper()
    if is_tcpip_resource(resource):
        host_ip = parse_tcpip_host_ip(resource)
        if host_ip is not None:
            tail = resource.split("::")[2:]
            numeric_tail: list[int | str] = []
            for part in tail:
                if part.isdigit():
                    numeric_tail.append(int(part))
                else:
                    numeric_tail.append(part.lower())
            return (tuple(int(o) for o in str(host_ip).split(".")), tuple(numeric_tail))
        return (resource.lower(),)

    match = _GPIB_RE.match(upper)
    if match:
        return (int(match.group(1)), int(match.group(2)))

    match = _USB_RE.match(resource)
    if match:
        serial = match.group(4) or ""
        return (
            int(match.group(1)),
            int(match.group(2), 16),
            int(match.group(3), 16),
            serial.lower(),
        )

    match = _ASRL_RE.match(upper)
    if match:
        return (int(match.group(1)), resource.lower())

    match = _PXI_RE.match(upper)
    if match:
        return (int(match.group(1)), resource.lower())

    return (resource.lower(),)


def resource_sort_key(resource: str) -> tuple[Any, ...]:
    """Compute a global sort key for ``resource`` (connection type, then address)."""
    return (_interface_rank(resource), _address_sort_key(resource))


def sort_resources(resources: list[str]) -> list[str]:
    """Return ``resources`` sorted for stable autoconfig ID assignment."""
    return sorted(resources, key=resource_sort_key)
