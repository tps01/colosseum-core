"""Windows host collectors (ctypes, pyserial)."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Any


def _kernel32() -> Any:  # noqa: ANN401
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        raise OSError("Windows API unavailable")
    return windll.kernel32


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
