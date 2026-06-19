"""Linux host collectors (/proc, pyserial, network)."""

from __future__ import annotations

import fcntl
import ipaddress
import socket
import struct
from pathlib import Path

from .network import IPv4NetworkBinding

SIOCGIFADDR = 0x8915
SIOCGIFNETMASK = 0x891B


def _ioctl_ipv4(name: str, request: int) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        ifreq = struct.pack("256s", name[:15].encode())
        result = fcntl.ioctl(sock.fileno(), request, ifreq)
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


def memory_available_mb() -> float:
    meminfo = Path("/proc/meminfo").read_text(encoding="utf-8")
    for line in meminfo.splitlines():
        if line.startswith("MemAvailable:"):
            kb = int(line.split()[1])
            return kb / 1024.0
    raise OSError("MemAvailable not found in /proc/meminfo")


def uptime_s() -> float:
    uptime = Path("/proc/uptime").read_text(encoding="utf-8").split()
    return float(uptime[0])


def serial_ports_csv() -> str:
    try:
        from serial.tools import list_ports
    except ImportError:
        return ""
    names = sorted(port.device for port in list_ports.comports() if "/dev/tty" in port.device)
    return ",".join(names)
