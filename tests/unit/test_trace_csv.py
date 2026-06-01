"""Trace CSV helpers for spectrum analyzers."""

from __future__ import annotations

import pytest

from colosseum_equipment.instruments.speca.trace_csv import (
    frequency_axis,
    parse_trace_amplitudes,
    write_trace_csv,
)


def test_parse_trace_amplitudes() -> None:
    assert parse_trace_amplitudes("-42.5,-41.0,-40.5") == [-42.5, -41.0, -40.5]


def test_frequency_axis_endpoints() -> None:
    freqs = frequency_axis(1e9, 10e6, 3)
    assert freqs[0] == pytest.approx(995e6)
    assert freqs[1] == pytest.approx(1e9)
    assert freqs[2] == pytest.approx(1005e6)


def test_write_trace_csv_with_frequency(tmp_path) -> None:
    path = tmp_path / "trace.csv"
    write_trace_csv(path, [-42.0, -41.0], center_hz=1e9, span_hz=10e6, include_frequency=True)
    text = path.read_text(encoding="utf-8")
    assert "frequency_hz,amplitude_dbm" in text
    assert "-42.000000" in text
