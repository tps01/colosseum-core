"""Linux host collectors (/proc, pyserial)."""

from __future__ import annotations

from pathlib import Path


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
    except ImportError as exc:
        raise ImportError(
            "pyserial is required for serial port enumeration. "
            "Install with: pip install colosseum[hardware]"
        ) from exc
    names = sorted(port.device for port in list_ports.comports() if "/dev/tty" in port.device)
    return ",".join(names)
