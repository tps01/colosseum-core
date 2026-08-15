"""Linux IPv4 interface binding collection."""

from __future__ import annotations

import ipaddress
import socket
import struct
from typing import Any

from .bindings import IPv4NetworkBinding

_fcntl_mod: Any = None
try:
    import fcntl

    _fcntl_mod = fcntl
except ModuleNotFoundError:
    pass

SIOCGIFADDR = 0x8915
SIOCGIFNETMASK = 0x891B


def _ioctl_ipv4(name: str, request: int) -> str:
    if _fcntl_mod is None:
        raise OSError("fcntl is not available on this platform")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        ifreq = struct.pack("256s", name[:15].encode())
        result = _fcntl_mod.ioctl(sock.fileno(), request, ifreq)
        return socket.inet_ntoa(result[20:24])
    finally:
        sock.close()


def list_ipv4_network_bindings() -> list[IPv4NetworkBinding]:
    bindings: list[IPv4NetworkBinding] = []
    try:
        interfaces = socket.if_nameindex()
    except OSError:
        return bindings
    for _idx, name in interfaces:
        if name == "lo":
            continue
        try:
            address = _ioctl_ipv4(name, SIOCGIFADDR)
            netmask = _ioctl_ipv4(name, SIOCGIFNETMASK)
        except OSError:
            continue
        try:
            iface = ipaddress.IPv4Interface(f"{address}/{netmask}")
        except ValueError:
            continue
        bindings.append(
            IPv4NetworkBinding(
                interface=name,
                address=str(iface.ip),
                network=str(iface.network.network_address),
                prefix=iface.network.prefixlen,
            )
        )
    return bindings
