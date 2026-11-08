"""Record in-process soak metrics each suite repeat (R-SOAK-02 fixture)."""

from __future__ import annotations


def _rss_mb() -> float:
    """Return this process's resident set size in mebibytes.

    A missing or zero reading is a failed measurement. Callers must not treat
    that as a passed memory gate.
    """
    import sys

    rss = _read_rss_mb(sys.platform)
    if rss <= 0:
        raise RuntimeError(f"RSS measurement unavailable or zero ({rss} MiB)")
    return rss


def _read_rss_mb(platform: str) -> float:
    from pathlib import Path

    if platform == "win32":
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        get_current_process = kernel32.GetCurrentProcess
        get_current_process.restype = wintypes.HANDLE
        get_memory_info = psapi.GetProcessMemoryInfo
        get_memory_info.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
            wintypes.DWORD,
        ]
        get_memory_info.restype = wintypes.BOOL

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        if not get_memory_info(get_current_process(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return counters.WorkingSetSize / (1024 * 1024)

    status = Path("/proc/self/status")
    if status.is_file():
        for line in status.read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return float(line.split()[1]) / 1024.0
        raise RuntimeError("VmRSS missing from /proc/self/status")

    import resource

    usage = resource.getrusage(resource.RUSAGE_SELF)
    rss = usage.ru_maxrss
    if platform == "darwin":
        return rss / (1024 * 1024)
    return rss / 1024.0


def main() -> None:
    import gc

    from colosseum.context import get_context

    ctx = get_context()
    out = ctx.suite_output_dir
    if out is None:
        raise RuntimeError("soak_probe requires an allocated suite container")

    cache_len = len(ctx.resource_cache)
    if cache_len > 0:
        raise RuntimeError(f"resource_cache must stay empty during soak, got {cache_len}")

    col_count = sum(
        1
        for obj in gc.get_objects()
        if isinstance(getattr(type(obj), "__module__", None), str)
        and type(obj).__module__.startswith("colosseum")
    )
    gc_count = len(gc.get_objects())
    repeat = ctx.slot_repeat_index if ctx.slot_repeat_index is not None else -1

    path = out / "soak_metrics.tsv"
    write_header = not path.exists()
    with path.open("a", encoding="utf-8") as handle:
        if write_header:
            handle.write(
                "repeat_index\trss_mb\tgc_objects\tcolosseum_objects\tresource_cache_len\n",
            )
        handle.write(
            f"{repeat}\t{_rss_mb():.3f}\t{gc_count}\t{col_count}\t{cache_len}\n",
        )
