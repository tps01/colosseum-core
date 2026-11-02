"""Duration and frequency strings on decorated plugin commands."""

from __future__ import annotations

import math

import pytest
from colosseum.decorators import command, measurement
from colosseum.units import coerce_units, parse_duration, parse_frequency


def test_parse_duration_suffix() -> None:
    assert parse_duration("61s") == pytest.approx(61.0)
    assert parse_duration("500ms") == pytest.approx(0.5)
    assert parse_duration(2) == pytest.approx(2.0)
    assert parse_duration("1us") == pytest.approx(1e-6)
    assert parse_duration("1µs") == pytest.approx(1e-6)
    assert parse_duration("1w") == pytest.approx(604800.0)
    assert parse_duration("1d") == pytest.approx(86400.0)
    assert parse_duration("1h30m") == pytest.approx(5400.0)


def test_parse_duration_rejects_empty_negative_and_nonfinite() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_duration("")
    with pytest.raises(ValueError, match="empty"):
        parse_duration(" ")
    with pytest.raises(ValueError, match="non-negative"):
        parse_duration(-1)
    with pytest.raises(ValueError, match="finite"):
        parse_duration(math.inf)


def test_parse_frequency_units() -> None:
    assert parse_frequency("1GHz") == pytest.approx(1e9)
    assert parse_frequency("10 MHz") == pytest.approx(10e6)
    assert parse_frequency("100kHz") == pytest.approx(1e5)
    assert parse_frequency("1Hz") == pytest.approx(1.0)
    assert parse_frequency(1_000_000) == pytest.approx(1e6)
    assert parse_frequency("1e6") == pytest.approx(1e6)


def test_parse_frequency_rejects_bad_types_and_duration_suffix() -> None:
    with pytest.raises(ValueError, match="Invalid frequency"):
        parse_frequency("61s")
    with pytest.raises(ValueError, match="Invalid frequency"):
        parse_frequency(True)
    with pytest.raises(ValueError, match="Invalid frequency"):
        parse_frequency(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="empty"):
        parse_frequency(" ")
    with pytest.raises(ValueError, match="non-negative"):
        parse_frequency(-1.0)


def test_coerce_units_classifiers() -> None:
    converted = coerce_units(
        {
            "timeout_s": "500ms",
            "span_hz": "10kHz",
            "rbw": "1kHz",
            "vbw": "100Hz",
            "span": "1MHz",
            "expected_s": "1s",
            "position_s": "2s",
            "rate_per_s": "3s",
            "label": "keep",
        }
    )
    assert converted["timeout_s"] == pytest.approx(0.5)
    assert converted["span_hz"] == pytest.approx(1e4)
    assert converted["rbw"] == pytest.approx(1e3)
    assert converted["vbw"] == pytest.approx(100.0)
    assert converted["span"] == pytest.approx(1e6)
    assert converted["expected_s"] == "1s"
    assert converted["position_s"] == "2s"
    assert converted["rate_per_s"] == "3s"
    assert converted["label"] == "keep"


@command
def _timed(*, timeout: float = 30.0) -> float:
    return timeout


@command
def _tuned(*, frequency: float, span_hz: float = 1.0) -> tuple[float, float]:
    return frequency, span_hz


@measurement
def _remote(*, key: str, timeout: float = 30.0) -> float:
    _ = key
    return timeout


def test_command_accepts_duration_and_frequency(unit_runtime_context: object) -> None:
    assert _timed(timeout="61s") == pytest.approx(61.0)
    assert _tuned(frequency="1GHz", span_hz="10MHz") == (
        pytest.approx(1e9),
        pytest.approx(10e6),
    )
    assert _tuned(frequency=2_400_000_000.0) == (pytest.approx(2.4e9), pytest.approx(1.0))
    _ = unit_runtime_context


def test_measurement_timeout_duration(unit_runtime_context: object) -> None:
    assert _remote(key="ssh", timeout="61s") == pytest.approx(61.0)
    _ = unit_runtime_context


def test_bad_frequency_is_a_command_error(unit_runtime_context: object) -> None:
    with pytest.raises(ValueError, match="frequency"):
        _tuned(frequency="61s")
    row = unit_runtime_context.db.fetch_table_rows("commands")[-1]
    assert row["status"] == "ERROR"
