"""High-level spectrum analyzer APIs exposed as ``col.equipment.speca``.

Configure instruments with ``[[equipment.speca]]`` in bench TOML (``speca_id``, ``driver``,
``resource``, optional ``model``). Trace and capture files are written under the active run
output directory and registered as artifacts. Unsupported operations raise
:class:`~colosseum_equipment.exceptions.EquipmentCapabilityError`.
"""

from __future__ import annotations

from colosseum.decorators import measurement

from colosseum_equipment.connections import get_cached_instrument


def set_center_frequency(*, speca_id: int, frequency: float) -> None:
    """Set spectrum center frequency in hertz."""
    get_cached_instrument("speca", speca_id).set_center_frequency(frequency)


def set_span(*, speca_id: int, span: float) -> None:
    """Set frequency span in hertz."""
    get_cached_instrument("speca", speca_id).set_span(span)


def set_rbw(*, speca_id: int, rbw: float) -> None:
    """Set resolution bandwidth in hertz."""
    get_cached_instrument("speca", speca_id).set_rbw(rbw)


def peak_search(*, speca_id: int, marker: int = 1) -> None:
    """Run a peak search and move the given marker to the peak."""
    get_cached_instrument("speca", speca_id).peak_search(marker)


@measurement
def measure_marker_power(*, speca_id: int, marker: int = 1, key: str) -> float:
    """Read marker amplitude in dBm and persist a measurement row."""
    return get_cached_instrument("speca", speca_id).measure_marker_power(marker)


@measurement
def measure_marker_frequency(*, speca_id: int, marker: int = 1, key: str) -> float:
    """Read marker frequency in hertz and persist a measurement row."""
    return get_cached_instrument("speca", speca_id).measure_marker_frequency(marker)


def save_trace_data(
    *,
    speca_id: int,
    path: str,
    trace: int = 1,
    include_frequency: bool = True,
) -> None:
    """Export trace data to a CSV under the run directory and register an artifact.

    Args:
        speca_id: Configured spectrum analyzer id.
        path: Relative path under the output directory (for example ``traces/sweep.csv``).
        trace: Trace number (1-based).
        include_frequency: When True, CSV columns are ``frequency_hz,amplitude_dbm``.
    """
    get_cached_instrument("speca", speca_id).save_trace_data(
        path,
        trace=trace,
        include_frequency=include_frequency,
    )


def preset(*, speca_id: int) -> None:
    """Return the instrument to a default preset state."""
    get_cached_instrument("speca", speca_id).preset()


def set_reference_level(*, speca_id: int, level_dbm: float) -> None:
    """Set display reference level in dBm."""
    get_cached_instrument("speca", speca_id).set_reference_level(level_dbm)


def set_vbw(*, speca_id: int, vbw: float) -> None:
    """Set video bandwidth in hertz."""
    get_cached_instrument("speca", speca_id).set_vbw(vbw)


def set_sweep_time(*, speca_id: int, seconds: float) -> None:
    """Set sweep time in seconds."""
    get_cached_instrument("speca", speca_id).set_sweep_time(seconds)


def set_detector(*, speca_id: int, detector: str) -> None:
    """Set trace detector mode (model-specific, for example ``APEak``)."""
    get_cached_instrument("speca", speca_id).set_detector(detector)


def set_trace_mode(*, speca_id: int, trace: int, mode: str) -> None:
    """Set trace mode (for example ``WRIT``, ``MAXH``, ``AVER``)."""
    get_cached_instrument("speca", speca_id).set_trace_mode(trace, mode)


def set_continuous_sweep(*, speca_id: int, enabled: bool) -> None:
    """Enable or disable continuous sweep."""
    get_cached_instrument("speca", speca_id).set_continuous_sweep(enabled)


def single_sweep(*, speca_id: int) -> None:
    """Trigger a single sweep and wait for completion."""
    get_cached_instrument("speca", speca_id).single_sweep()


def save_screenshot(*, speca_id: int, path: str) -> None:
    """Save a display screenshot and register an artifact (vendor-specific)."""
    get_cached_instrument("speca", speca_id).save_screenshot(path)


def download_capture(*, speca_id: int, path: str, kind: str = "iq") -> None:
    """Download IQ or other capture data (``tektronix-rsa5100b`` only)."""
    get_cached_instrument("speca", speca_id).download_capture(path, kind)


def save_spectrogram(*, speca_id: int, path: str) -> None:
    """Save a spectrogram file (``tektronix-rsa5100b`` only)."""
    get_cached_instrument("speca", speca_id).save_spectrogram(path)


def configure_trigger(*, speca_id: int, source: str = "IMM") -> None:
    """Configure acquisition trigger source (RTSA models)."""
    get_cached_instrument("speca", speca_id).configure_trigger(source)


def set_acquisition_length(*, speca_id: int, seconds: float) -> None:
    """Set RTSA acquisition length in seconds."""
    get_cached_instrument("speca", speca_id).set_acquisition_length(seconds)
