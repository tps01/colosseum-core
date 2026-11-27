"""Duration and frequency strings on decorated plugin commands."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pytest
from colosseum.decorators import command, measurement
from colosseum.units import coerce_units, parse_duration, parse_frequency, unit_inputs


if TYPE_CHECKING:
    from colosseum.context import RuntimeContext


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


@pytest.mark.parametrize("text", ["10e3kHz", "10e6 Hz", "10MHz", "10 MHz"])
def test_parse_frequency_equivalent_spellings(text: str) -> None:
    assert parse_frequency(text) == 1e7


@pytest.mark.parametrize(("text", "hertz"), [("  2.5E-1 MHz  ", 2.5e5), ("1e+2Hz", 100.0), ("1e-325 GHz", 1e-316)])
def test_parse_frequency_scales_before_float_conversion(text: str, hertz: float) -> None:
    assert parse_frequency(text) == hertz


@pytest.mark.parametrize("text", ["10e kHz", "10e+Hz", "10e2 qHz", "-10e3kHz", "1e308 GHz"])
def test_parse_frequency_rejects_invalid_exponent_values(text: str) -> None:
    with pytest.raises(ValueError):
        parse_frequency(text)


@pytest.mark.parametrize("text", ["10 Mhz", "10e3khz", "1KHz", "1ghz", "1HZ"])
def test_parse_frequency_requires_canonical_suffix_case(text: str) -> None:
    with pytest.raises(ValueError, match="Invalid frequency"):
        parse_frequency(text)


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
    assert _tuned(frequency="1e3MHz", span_hz="10e3kHz") == (
        pytest.approx(1e9),
        pytest.approx(10e6),
    )
    assert _tuned(frequency=2_400_000_000.0) == (pytest.approx(2.4e9), pytest.approx(1.0))
    _ = unit_runtime_context


def test_dry_run_validates_scientific_frequency(unit_runtime_context: RuntimeContext) -> None:
    unit_runtime_context.run_options.dry_run = True

    @command
    def tune(*, frequency: float) -> None:
        raise AssertionError(f"dry run invoked command with {frequency}")

    assert tune(frequency="10e3kHz") is None
    assert unit_runtime_context.result_aggregator._records[0]["status"] == "DRY"  # noqa: SLF001
    assert unit_runtime_context.result_aggregator.overall_pass()


def test_measurement_timeout_duration(unit_runtime_context: object) -> None:
    assert _remote(key="ssh", timeout="61s") == pytest.approx(61.0)
    _ = unit_runtime_context


def test_bad_frequency_is_a_command_error(unit_runtime_context: object) -> None:
    with pytest.raises(ValueError, match="frequency"):
        _tuned(frequency="61s")
    row = unit_runtime_context.db.fetch_table_rows("commands")[-1]
    assert row["status"] == "ERROR"


@pytest.mark.parametrize(("text", "seconds"), [("1e3 ms", 1.0), ("1h 30m", 5400.0), ("10 ns", 1e-8)])
def test_duration_accepts_scientific_notation_and_spacing(text: str, seconds: float) -> None:
    assert parse_duration(text) == seconds


@pytest.mark.parametrize("text", ["1Ms", "1MS", "1S", "1h-30m"])
def test_duration_rejects_uppercase_and_negative_components(text: str) -> None:
    with pytest.raises(ValueError):
        parse_duration(text)


@pytest.mark.parametrize(("text", "ohms"), [("47R", 47.0), ("2 kR", 2000.0), ("1 MR", 1e6), ("2 mR", 0.002)])
def test_resistance_accepts_uppercase_r(text: str, ohms: float) -> None:
    def input_value() -> None:
        pass

    tagged = unit_inputs(resistance="ohm")(input_value)
    assert coerce_units({"resistance": text}, func=tagged)["resistance"] == ohms
    with pytest.raises(ValueError, match="resistance"):
        coerce_units({"resistance": "2 kr"}, func=tagged)


def test_declared_quantities_match_the_parameter_dimension(unit_runtime_context: RuntimeContext) -> None:
    @command
    @unit_inputs(voltage="V", power="W", resistance="ohm", slew="A/s")
    def apply(*, voltage: float, power: float, resistance: float, slew: float) -> tuple[float, ...]:
        return voltage, power, resistance, slew

    assert apply(voltage="-500 mV", power="2e-1 kW", resistance="2 kohm", slew="50 mA/s") == (
        -0.5, 200.0, 2000.0, 0.05,
    )
    with pytest.raises(ValueError, match="power: Invalid W"):
        apply(voltage=1.0, power="2 dBm", resistance=2.0, slew=3.0)
    assert parse_frequency("1mHz") == 1e-3
    assert parse_frequency("1MHz") == 1e6
    assert parse_frequency("1THz") == 1e12
    unit_runtime_context.run_options.dry_run = True
    assert apply(voltage="-500 mV", power="2e-1 kW", resistance="2 kohm", slew="50 mA/s") is None
