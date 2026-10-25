"""Duration and frequency strings on decorated plugin commands."""

from __future__ import annotations

import pytest
from colosseum.decorators import command, measurement
from colosseum.units import parse_duration, parse_frequency


def test_parse_duration_suffix() -> None:
    assert parse_duration("61s") == pytest.approx(61.0)
    assert parse_duration("500ms") == pytest.approx(0.5)
    assert parse_duration(2) == pytest.approx(2.0)


def test_parse_frequency_units() -> None:
    assert parse_frequency("1GHz") == pytest.approx(1e9)
    assert parse_frequency("10 MHz") == pytest.approx(10e6)
    assert parse_frequency("100kHz") == pytest.approx(1e5)
    assert parse_frequency("1Hz") == pytest.approx(1.0)
    assert parse_frequency(1_000_000) == pytest.approx(1e6)
    assert parse_frequency("1e6") == pytest.approx(1e6)


def test_parse_frequency_rejects_duration_suffix() -> None:
    with pytest.raises(ValueError, match="Invalid frequency"):
        parse_frequency("61s")


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
