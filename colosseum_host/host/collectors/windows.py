"""Windows host collectors (ctypes, pyserial, network)."""

from __future__ import annotations

import ctypes
import ipaddress
import socket
from ctypes import wintypes
from typing import Any

from .network import IPv4NetworkBinding


def _kernel32() -> Any:  # noqa: ANN401
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        raise OSError("Windows API unavailable")
    return windll.kernel32


def _iphlpapi() -> Any:  # noqa: ANN401
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        raise OSError("Windows API unavailable")
    return windll.iphlpapi


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class _IP_ADAPTER_ADDRESSES(ctypes.Structure):
    pass


_IP_ADAPTER_ADDRESSES._fields_ = [
    ("Length", wintypes.ULONG),
    ("IfIndex", wintypes.DWORD),
    ("Next", ctypes.POINTER(_IP_ADAPTER_ADDRESSES)),
    ("AdapterName", ctypes.c_char_p),
    ("FirstUnicastAddress", ctypes.c_void_p),
    ("FirstAnycastAddress", ctypes.c_void_p),
    ("FirstMulticastAddress", ctypes.c_void_p),
    ("FirstDnsServerAddress", ctypes.c_void_p),
    ("DnsSuffix", wintypes.LPWSTR),
    ("Description", wintypes.LPWSTR),
    ("FriendlyName", wintypes.LPWSTR),
    ("PhysicalAddress", wintypes.BYTE * 8),
    ("PhysicalAddressLength", wintypes.DWORD),
    ("Flags", wintypes.DWORD),
    ("Mtu", wintypes.DWORD),
    ("IfType", wintypes.DWORD),
    ("OperStatus", wintypes.DWORD),
    ("Ipv6IfIndex", wintypes.DWORD),
    ("ZoneIndices", wintypes.DWORD * 16),
    ("FirstPrefix", ctypes.c_void_p),
]


class _SOCKET_ADDRESS(ctypes.Structure):
    _fields_ = [
        ("lpSockaddr", ctypes.c_void_p),
        ("iSockaddrLength", ctypes.c_int),
    ]


class _IP_ADAPTER_UNICAST_ADDRESS(ctypes.Structure):
    pass


_IP_ADAPTER_UNICAST_ADDRESS._fields_ = [
    ("Length", wintypes.ULONG),
    ("Flags", wintypes.DWORD),
    ("Next", ctypes.POINTER(_IP_ADAPTER_UNICAST_ADDRESS)),
    ("Address", _SOCKET_ADDRESS),
    ("PrefixOrigin", ctypes.c_int),
    ("SuffixOrigin", ctypes.c_int),
    ("DadState", ctypes.c_int),
    ("ValidLifetime", wintypes.ULONG),
    ("PreferredLifetime", wintypes.ULONG),
    ("LeaseLifetime", wintypes.ULONG),
    ("OnLinkPrefixLength", ctypes.c_ubyte),
]


def list_ipv4_network_bindings() -> list[IPv4NetworkBinding]:
    bindings: list[IPv4NetworkBinding] = []
    try:
        size = wintypes.ULONG(15000)
        buffer = ctypes.create_string_buffer(size.value)
        flags = 0
        family = socket.AF_INET
        result = _iphlpapi().GetAdaptersAddresses(
            family,
            flags,
            None,
            ctypes.byref(_IP_ADAPTER_ADDRESSES.from_buffer(buffer)),
            ctypes.byref(size),
        )
        if result == 111:
            buffer = ctypes.create_string_buffer(size.value)
            result = _iphlpapi().GetAdaptersAddresses(
                family,
                flags,
                None,
                ctypes.byref(_IP_ADAPTER_ADDRESSES.from_buffer(buffer)),
                ctypes.byref(size),
            )
        if result != 0:
            return bindings

        adapter = _IP_ADAPTER_ADDRESSES.from_buffer(buffer)
        while True:
            name = adapter.FriendlyName or adapter.Description or adapter.AdapterName or ""
            if isinstance(name, bytes):
                interface = name.decode("utf-8", errors="replace")
            else:
                interface = str(name)
            unicast_ptr = adapter.FirstUnicastAddress
            while unicast_ptr:
                addr_struct = _IP_ADAPTER_UNICAST_ADDRESS.from_address(unicast_ptr)
                sa = addr_struct.Address
                if sa.iSockaddrLength >= 28 and sa.lpSockaddr:
                    sockaddr = (ctypes.c_ubyte * sa.iSockaddrLength).from_address(sa.lpSockaddr)
                    family_value = int.from_bytes(sockaddr[0:2], "little")
                    if family_value == socket.AF_INET:
                        ip_bytes = bytes(sockaddr[4:8])
                        address = socket.inet_ntoa(ip_bytes)
                        prefix = int(addr_struct.OnLinkPrefixLength)
                        if prefix == 0:
                            prefix = 24
                        try:
                            iface = ipaddress.IPv4Interface(f"{address}/{prefix}")
                        except ValueError:
                            unicast_ptr = addr_struct.Next or None
                            continue
                        bindings.append(
                            IPv4NetworkBinding(
                                interface=interface,
                                address=str(iface.ip),
                                network=str(iface.network.network_address),
                                prefix=iface.network.prefixlen,
                            )
                        )
                next_unicast = addr_struct.Next
                unicast_ptr = next_unicast if next_unicast else None
            next_adapter = adapter.Next
            if not next_adapter:
                break
            adapter = next_adapter.contents
    except (AttributeError, OSError, ValueError):
        return bindings
    return bindings


def memory_available_mb() -> float:
    stat = _MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
    if not _kernel32().GlobalMemoryStatusEx(ctypes.byref(stat)):
        raise OSError("GlobalMemoryStatusEx failed")
    return float(stat.ullAvailPhys) / (1024**2)


def uptime_s() -> float:
    return float(_kernel32().GetTickCount64()) / 1000.0


def serial_ports_csv() -> str:
    try:
        from serial.tools import list_ports
    except ImportError:
        return ""
    names = sorted(
        port.device for port in list_ports.comports() if port.device.upper().startswith("COM")
    )
    return ",".join(names)
