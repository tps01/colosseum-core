"""Deterministic checks for the in-process soak gate.

These do not launch a soak. They fail when the growth windows overlap or the
platform RSS probe cannot measure this process.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from tests.regression.run_soak_inprocess import MIN_GROWTH_ROWS, WINDOW_ROWS, SoakRow, _check_growth

_PROBE = Path(__file__).resolve().parents[1] / "fixtures" / "scripts" / "soak_probe.py"


def _load_probe():
    spec = importlib.util.spec_from_file_location("soak_probe_under_test", _PROBE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_platform_rss_probe_measures_this_process() -> None:
    rss = _load_probe()._rss_mb()
    assert rss > 0


def test_growth_check_rejects_overlapping_windows_and_real_growth() -> None:
    overlapping = [SoakRow(i, float(i * 100), 0, 0, 0) for i in range(MIN_GROWTH_ROWS - WINDOW_ROWS)]
    assert _check_growth(overlapping)

    growing = [SoakRow(i, float(i * 100), i, i, 0) for i in range(MIN_GROWTH_ROWS)]
    failures = _check_growth(growing)
    assert any(item.startswith("RSS grew") for item in failures)

    flat = [SoakRow(i, 12.0, 4, 4, 0) for i in range(MIN_GROWTH_ROWS)]
    assert _check_growth(flat) == []
