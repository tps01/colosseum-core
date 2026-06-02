"""Trace CSV helpers for spectrum analyzers."""

from __future__ import annotations

import pytest

from colosseum_equipment.instruments.speca.trace_csv import (
    frequency_axis,
    nearest_trace_bin,
    parse_trace_amplitudes,
    read_trace_power_at_frequency,
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


def test_nearest_trace_bin_picks_closest_frequency() -> None:
    frequencies = [995e6, 1e9, 1005e6]
    assert nearest_trace_bin(frequencies, 1.004e9) == 2
    assert nearest_trace_bin(frequencies, 1e9) == 1


def test_read_trace_power_at_frequency(tmp_path) -> None:
    path = tmp_path / "trace.csv"
    write_trace_csv(path, [-42.5, -41.0, -40.5], center_hz=1e9, span_hz=10e6, include_frequency=True)
    power, actual_hz = read_trace_power_at_frequency(path, 1e9)
    assert power == pytest.approx(-41.0)
    assert actual_hz == pytest.approx(1e9)
    edge_power, _ = read_trace_power_at_frequency(path, 995e6)
    assert edge_power == pytest.approx(-42.5)
