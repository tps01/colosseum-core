"""Vector network analyzer APIs exposed as ``col.equipment.vna``.

Configure instruments with ``[[equipment.vna]]`` in bench TOML (``vna_id``, ``resource``,
optional ``model``, ``channel``, and ``driver``; default driver is VISA/SCPI). Trace exports are
written under the active run output directory. Unsupported operations on ``anritsu-541xx`` raise
:class:`~colosseum_equipment.exceptions.EquipmentCapabilityError`.
"""

from __future__ import annotations

from colosseum.decorators import command, measurement

from colosseum_equipment.api._verify import tolerance_verifier
from colosseum_equipment.connections import get_cached_instrument


@command
def preset(*, vna_id: int) -> None:
    """Return the VNA to a default preset.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).preset()


@command
def set_start_frequency(*, vna_id: int, frequency_hz: float) -> None:
    """Set the sweep start frequency.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param frequency_hz: Start frequency in hertz.
    :type frequency_hz: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).set_start_frequency(frequency_hz)


@command
def set_stop_frequency(*, vna_id: int, frequency_hz: float) -> None:
    """Set the sweep stop frequency.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param frequency_hz: Stop frequency in hertz.
    :type frequency_hz: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).set_stop_frequency(frequency_hz)


@command
def set_points(*, vna_id: int, count: int) -> None:
    """Set the number of sweep points.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param count: Number of frequency points in the sweep.
    :type count: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).set_points(count)


@command
def single_sweep(*, vna_id: int) -> None:
    """Trigger a single sweep and wait for completion.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).single_sweep()


@command
def wait_complete(*, vna_id: int) -> None:
    """Block until the current operation completes.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).wait_complete()


@command
def toggle_display(*, vna_id: int, enabled: bool) -> None:
    """Enable or disable instrument display updates.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param enabled: ``True`` to enable display updates, ``False`` to disable.
    :type enabled: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).toggle_display(enabled)


@command
def perform_ecal(*, vna_id: int, ports: str) -> None:
    """Run guided e-calibration between ports.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param ports: Port pair for calibration (for example ``1:4``).
    :type ports: str

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).perform_ecal(ports)


@command
def set_marker(*, vna_id: int, marker: int, frequency_hz: float, trace: int = 1) -> None:
    """Place a marker at the given frequency on a trace.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param marker: Marker number.
    :type marker: int
    :param frequency_hz: Marker frequency in hertz.
    :type frequency_hz: float
    :param trace: Trace number (default ``1``).
    :type trace: int, optional

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).set_marker(marker, frequency_hz, trace=trace)


@measurement
def measure_marker_frequency(*, vna_id: int, marker: int = 1, key: str) -> float:
    """Read marker frequency.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param marker: Marker number (default ``1``).
    :type marker: int, optional
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured marker frequency in hertz.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("vna", vna_id).measure_marker_frequency(marker))


@measurement
def measure_marker_value(*, vna_id: int, marker: int = 1, key: str) -> float:
    """Read marker trace value.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param marker: Marker number (default ``1``).
    :type marker: int, optional
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured marker trace value.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("vna", vna_id).measure_marker_value(marker))


verify_marker_frequency = tolerance_verifier(
    "measure_marker_frequency",
    name="verify_marker_frequency",
    default_tolerance=1000.0,
)


verify_marker_value = tolerance_verifier(
    "measure_marker_value",
    name="verify_marker_value",
    default_tolerance=0.01,
)


@command
def save_trace_data(
    *,
    vna_id: int,
    path: str,
    trace: int = 1,
    file_format: str = "csv",
    parameter: str = "S11",
) -> None:
    """Export trace data to CSV or Touchstone S2P under the run directory.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param path: Relative path under the run directory.
    :type path: str
    :param trace: Trace number to export (default ``1``).
    :type trace: int, optional
    :param file_format: Export format, ``csv`` or ``s2p`` (default ``csv``).
    :type file_format: str, optional
    :param parameter: S-parameter name for S2P export (default ``S11``).
    :type parameter: str, optional

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).save_trace_data(
        path,
        trace=trace,
        file_format=file_format,
        parameter=parameter,
    )


@command
def set_if_bw(*, vna_id: int, bandwidth_hz: float) -> None:
    """Set IF/resolution bandwidth.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param bandwidth_hz: IF bandwidth in hertz.
    :type bandwidth_hz: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).set_if_bw(bandwidth_hz)


@command
def set_tx_power(*, vna_id: int, power_dbm: float, port: int = 1) -> None:
    """Set source port output power.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param power_dbm: Output power in dBm.
    :type power_dbm: float
    :param port: Source port number (default ``1``).
    :type port: int, optional

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).set_tx_power(power_dbm, port=port)


@command
def set_rx_power(*, vna_id: int, power_dbm: float, port: int = 1) -> None:
    """Set receiver/reference level.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param power_dbm: Reference level in dBm.
    :type power_dbm: float
    :param port: Receiver port number (default ``1``).
    :type port: int, optional

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).set_rx_power(power_dbm, port=port)


@command
def set_sweep_time(*, vna_id: int, seconds: float) -> None:
    """Set sweep time.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param seconds: Sweep duration in seconds.
    :type seconds: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).set_sweep_time(seconds)


@command
def set_trace_count(*, vna_id: int, count: int) -> None:
    """Set the number of traces shown on the instrument.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param count: Number of traces.
    :type count: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).set_trace_count(count)


@command
def set_trace_hold(*, vna_id: int, trace: int, mode: str) -> None:
    """Configure trace hold mode.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param trace: Trace number.
    :type trace: int
    :param mode: Hold mode (for example ``MAXH``, ``MINH``, ``WRIT``, ``HOLD``).
    :type mode: str

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).set_trace_hold(trace, mode)


@command
def set_trace_parameters(*, vna_id: int, trace: int, parameter: str, format: str) -> None:
    """Set trace S-parameter and display format.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param trace: Trace number.
    :type trace: int
    :param parameter: S-parameter name (for example ``S11``).
    :type parameter: str
    :param format: Display format (for example ``MLOG``).
    :type format: str

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).set_trace_parameters(trace, parameter, format)


@command
def configure_trigger(
    *,
    vna_id: int,
    source: str = "IMM",
    continuous: bool | None = None,
    edge: str | None = None,
    delay_s: float | None = None,
    channel: int | None = None,
) -> None:
    """Configure acquisition trigger source and optional settings.

    :param vna_id: Configured ``equipment.vna`` id from bench TOML.
    :type vna_id: int
    :param source: Trigger source (default ``IMM``).
    :type source: str, optional
    :param continuous: ``True`` for continuous sweep, ``False`` for single sweep.
    :type continuous: bool | None, optional
    :param edge: Trigger edge (for example ``POS``, ``NEG``).
    :type edge: str | None, optional
    :param delay_s: Trigger delay in seconds.
    :type delay_s: float | None, optional
    :param channel: Measurement channel override.
    :type channel: int | None, optional

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vna", vna_id).configure_trigger(
        source,
        continuous=continuous,
        edge=edge,
        delay_s=delay_s,
        channel=channel,
    )
