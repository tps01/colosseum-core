"""Platform dispatch for host collectors."""

from __future__ import annotations

import sys

if sys.platform.startswith("win"):
    from . import windows as _platform
elif sys.platform.startswith("linux"):
    from . import linux as _platform
else:
    _platform = None  # type: ignore[assignment]


def memory_available_mb() -> float:
    if _platform is None:
        raise OSError(f"Unsupported platform for memory collection: {sys.platform}")
    return _platform.memory_available_mb()


def uptime_s() -> float:
    if _platform is None:
        raise OSError(f"Unsupported platform for uptime collection: {sys.platform}")
    return _platform.uptime_s()


def serial_ports_csv() -> str:
    if _platform is None:
        return ""
    return _platform.serial_ports_csv()
