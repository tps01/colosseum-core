"""Cross-platform host fact collectors (stdlib-first)."""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path


def python_version() -> str:
    return platform.python_version()


def platform_name() -> str:
    return platform.system()


def machine() -> str:
    return platform.machine()


def hostname() -> str:
    return platform.node()


def cpu_count() -> float:
    return float(os.cpu_count() or 0)


def disk_free_gb(path: str | Path | None = None) -> float:
    target = Path(path) if path is not None else Path.cwd()
    usage = shutil.disk_usage(target)
    return usage.free / (1024**3)


def bench_config_env() -> str | None:
    return os.environ.get("COLOSSEUM_BENCH_CONFIG")
