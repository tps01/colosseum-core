"""High-level spectrum analyzer APIs exposed as ``col.equipment.speca``.

Configure instruments with ``[[equipment.speca]]`` in bench TOML (``speca_id``,
``resource``, optional ``model`` and ``driver``; default driver is VISA/SCPI).
Trace and capture files are written under the active run output directory and
registered as artifacts. Unsupported operations raise
:class:`~colosseum_equipment.exceptions.EquipmentCapabilityError`.
"""

from __future__ import annotations

from colosseum.decorators import command, measurement

from colosseum_equipment.api._verify import tolerance_verifier
from colosseum_equipment.connections import get_cached_instrument


@command
def set_center_frequency(*, speca_id: int, frequency: float) -> None:
    """Set spectrum center frequency in hertz.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param frequency: Center frequency in hertz.
    :type frequency: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).set_center_frequency(frequency)


@command
def set_span(*, speca_id: int, span: float) -> None:
    """Set frequency span in hertz.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param span: Frequency span in hertz.
    :type span: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).set_span(span)


@command
def set_start_frequency(*, speca_id: int, frequency_hz: float) -> None:
    """Set the start frequency of the span in hertz.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param frequency_hz: Start frequency in hertz.
    :type frequency_hz: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).set_start_frequency(frequency_hz)


@command
def set_stop_frequency(*, speca_id: int, frequency_hz: float) -> None:
    """Set the stop frequency of the span in hertz.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param frequency_hz: Stop frequency in hertz.
    :type frequency_hz: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).set_stop_frequency(frequency_hz)


@command
def set_rbw(*, speca_id: int, rbw: float) -> None:
    """Set resolution bandwidth in hertz.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param rbw: Resolution bandwidth in hertz.
    :type rbw: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).set_rbw(rbw)


@command
def peak_search(*, speca_id: int, marker: int = 1) -> None:
    """Run a peak search and move the given marker to the peak.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param marker: Marker number (1-based).
    :type marker: int, optional

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).peak_search(marker)


@command
def toggle_marker(*, speca_id: int, marker: int, enabled: bool) -> None:
    """Enable or disable a marker by id.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param marker: Marker number (1-based).
    :type marker: int
    :param enabled: ``True`` to enable the marker, ``False`` to disable.
    :type enabled: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).toggle_marker(marker, enabled)


@command
def next_peak_right(*, speca_id: int, marker: int = 1) -> None:
    """Move the marker to the next peak to the right.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param marker: Marker number (1-based).
    :type marker: int, optional

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).next_peak_right(marker)


@command
def next_peak_left(*, speca_id: int, marker: int = 1) -> None:
    """Move the marker to the next peak to the left.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param marker: Marker number (1-based).
    :type marker: int, optional

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).next_peak_left(marker)


@command
def next_highest_peak(*, speca_id: int, marker: int = 1) -> None:
    """Move the marker to the highest peak in the current span.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param marker: Marker number (1-based).
    :type marker: int, optional

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).next_highest_peak(marker)


@command
def set_marker_frequency(*, speca_id: int, marker: int, frequency_hz: float) -> None:
    """Place a marker at the given frequency in hertz.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param marker: Marker number (1-based).
    :type marker: int
    :param frequency_hz: Marker frequency in hertz.
    :type frequency_hz: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).set_marker_frequency(marker, frequency_hz)


@measurement
def measure_marker_power(*, speca_id: int, marker: int = 1, key: str) -> float:
    """Read marker amplitude in dBm and persist a measurement row.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param marker: Marker number (1-based).
    :type marker: int, optional
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Marker amplitude in dBm.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("speca", speca_id).measure_marker_power(marker))


@measurement
def measure_marker_frequency(*, speca_id: int, marker: int = 1, key: str) -> float:
    """Read marker frequency in hertz and persist a measurement row.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param marker: Marker number (1-based).
    :type marker: int, optional
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Marker frequency in hertz.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("speca", speca_id).measure_marker_frequency(marker))


verify_marker_frequency = tolerance_verifier(
    "measure_marker_frequency",
    name="verify_marker_frequency",
    default_tolerance=1000.0,
)


verify_marker_power = tolerance_verifier(
    "measure_marker_power",
    name="verify_marker_power",
    default_tolerance=0.5,
    unit="dBm",
)


@measurement
def measure_trace_power_at_frequency(
    *,
    speca_id: int,
    frequency_hz: float,
    key: str,
    trace_path: str | None = None,
) -> float:
    """Read trace power (dBm) at ``frequency_hz`` using the nearest CSV frequency bin.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param frequency_hz: Query frequency in hertz.
    :type frequency_hz: float
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str
    :param trace_path: Optional relative path to a prior trace CSV under the run directory.
    :type trace_path: str | None, optional

    :returns: Trace power in dBm at the nearest frequency bin.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    power_dbm, _actual_hz = get_cached_instrument(
        "speca", speca_id
    ).measure_trace_power_at_frequency(
        frequency_hz,
        trace_path=trace_path,
    )
    return float(power_dbm)


verify_trace_power_at_frequency = tolerance_verifier(
    "measure_trace_power_at_frequency",
    name="verify_trace_power_at_frequency",
    default_tolerance=0.5,
    unit="dBm",
)


@command
def save_trace_data(
    *,
    speca_id: int,
    path: str,
    trace: int = 1,
    include_frequency: bool = True,
    save_plot: bool = False,
    plot_path: str | None = None,
) -> None:
    """Export trace data to a CSV under the run directory and register an artifact.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param path: Relative path under the output directory (for example ``traces/sweep.csv``).
    :type path: str
    :param trace: Trace number (1-based).
    :type trace: int, optional
    :param include_frequency: When True, CSV columns are ``frequency_hz,amplitude_dbm``.
    :type include_frequency: bool, optional
    :param save_plot: When True, also write a PNG plot (``path`` with ``.png`` suffix).
    :type save_plot: bool, optional
    :param plot_path: Optional explicit PNG path under the run directory.
    :type plot_path: str | None, optional

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).save_trace_data(
        path,
        trace=trace,
        include_frequency=include_frequency,
        save_plot=save_plot,
        plot_path=plot_path,
    )


@measurement
def measure_bw(
    *,
    speca_id: int,
    start_hz: float,
    stop_hz: float,
    key: str,
    threshold_db: float = 3.0,
    smoothing_order: int = 0,
    trace: int = 1,
    trace_path: str | None = None,
) -> float:
    """Measure occupied bandwidth in hertz from a trace CSV or live sweep.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param start_hz: Lower frequency bound for bandwidth analysis in hertz.
    :type start_hz: float
    :param stop_hz: Upper frequency bound for bandwidth analysis in hertz.
    :type stop_hz: float
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str
    :param threshold_db: Power drop from peak used to define bandwidth edges in dB.
    :type threshold_db: float, optional
    :param smoothing_order: Savitzky-Golay smoothing order applied before edge detection.
    :type smoothing_order: int, optional
    :param trace: Trace number (1-based) when reading from the instrument.
    :type trace: int, optional
    :param trace_path: Optional relative path to a prior trace CSV under the run directory.
    :type trace_path: str | None, optional

    :returns: Occupied bandwidth in hertz.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(
        get_cached_instrument("speca", speca_id).measure_bw(
            start_hz,
            stop_hz,
            threshold_db=threshold_db,
            smoothing_order=smoothing_order,
            trace=trace,
            trace_path=trace_path,
        )
    )


verify_bandwidth = tolerance_verifier(
    "measure_bw",
    name="verify_bandwidth",
    default_tolerance=1000.0,
)


@command
def preset(*, speca_id: int) -> None:
    """Return the instrument to a default preset state.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).preset()


@command
def set_reference_level(*, speca_id: int, level_dbm: float) -> None:
    """Set display reference level in dBm.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param level_dbm: Reference level in dBm.
    :type level_dbm: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).set_reference_level(level_dbm)


@command
def set_vbw(*, speca_id: int, vbw: float) -> None:
    """Set video bandwidth in hertz.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param vbw: Video bandwidth in hertz.
    :type vbw: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).set_vbw(vbw)


@command
def set_sweep_time(*, speca_id: int, seconds: float) -> None:
    """Set sweep time in seconds.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param seconds: Sweep time in seconds.
    :type seconds: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).set_sweep_time(seconds)


@command
def set_sweep_points(*, speca_id: int, count: int) -> None:
    """Set the number of sweep points.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param count: Number of sweep points.
    :type count: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).set_sweep_points(count)


@command
def toggle_trigger_delay(*, speca_id: int, enabled: bool) -> None:
    """Enable or disable trigger delay.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param enabled: ``True`` to enable trigger delay, ``False`` to disable.
    :type enabled: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).toggle_trigger_delay(enabled)


@command
def set_trigger_delay(*, speca_id: int, delay_s: float) -> None:
    """Set trigger delay in seconds.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param delay_s: Trigger delay in seconds.
    :type delay_s: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).set_trigger_delay(delay_s)


@command
def set_trigger_source(*, speca_id: int, source: str) -> None:
    """Set trigger source (for example ``IMM``, ``VID``, ``LINE``, ``EXT``, ``RFB``, ``TV``).

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param source: Trigger source string accepted by the configured model.
    :type source: str

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).set_trigger_source(source)


@command
def user_preset(*, speca_id: int) -> None:
    """Recall user preset 1.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).user_preset()


@command
def set_detector(*, speca_id: int, detector: str) -> None:
    """Set trace detector mode (model-specific, for example ``APEak``).

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param detector: Detector mode string accepted by the configured model.
    :type detector: str

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).set_detector(detector)


@command
def set_trace_mode(*, speca_id: int, trace: int, mode: str) -> None:
    """Set trace mode (for example ``WRIT``, ``MAXH``, ``AVER``).

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param trace: Trace number (1-based).
    :type trace: int
    :param mode: Trace mode string accepted by the configured model.
    :type mode: str

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).set_trace_mode(trace, mode)


@command
def set_continuous_sweep(*, speca_id: int, enabled: bool) -> None:
    """Enable or disable continuous sweep.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param enabled: ``True`` for continuous sweep, ``False`` for single-sweep mode.
    :type enabled: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).set_continuous_sweep(enabled)


@command
def single_sweep(*, speca_id: int) -> None:
    """Trigger a single sweep and wait for completion.

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).single_sweep()


@command
def save_screenshot(*, speca_id: int, path: str) -> None:
    """Save a display screenshot and register an artifact (vendor-specific).

    :param speca_id: Configured ``equipment.speca`` id from bench TOML.
    :type speca_id: int
    :param path: Relative path under the output directory for the screenshot file.
    :type path: str

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("speca", speca_id).save_screenshot(path)
