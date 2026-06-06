"""Host collector platform helpers."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from colosseum_host.host.collectors import common, linux, windows


def test_disk_free_gb_uses_shutil(tmp_path) -> None:
    with patch("colosseum_host.host.collectors.common.shutil.disk_usage") as usage:
        usage.return_value = MagicMock(free=5 * 1024**3)
        assert common.disk_free_gb(tmp_path) == pytest.approx(5.0)


def test_linux_memory_available_mb_parses_meminfo() -> None:
    meminfo = "MemTotal:       16384000 kB\nMemAvailable:    2048000 kB\n"
    with patch.object(linux.Path, "read_text", return_value=meminfo):
        assert linux.memory_available_mb() == pytest.approx(2000.0)


def test_linux_uptime_s_reads_proc() -> None:
    with patch.object(linux.Path, "read_text", return_value="123.45 456.78\n"):
        assert linux.uptime_s() == pytest.approx(123.45)


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Windows-only ctypes path")
def test_windows_memory_available_mb() -> None:
    fake_kernel = MagicMock()
    fake_kernel.GlobalMemoryStatusEx.return_value = True
    with patch("colosseum_host.host.collectors.windows.ctypes.windll.kernel32", fake_kernel):
        assert windows.memory_available_mb() >= 0.0


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Windows-only ctypes path")
def test_windows_uptime_s() -> None:
    fake_kernel = MagicMock()
    fake_kernel.GetTickCount64.return_value = 60_000
    with patch("colosseum_host.host.collectors.windows.ctypes.windll.kernel32", fake_kernel):
        assert windows.uptime_s() == pytest.approx(60.0)
