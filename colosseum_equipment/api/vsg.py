"""High-level vector/signal generator APIs exposed as ``col.equipment.vsg``.

Configure instruments with ``[[equipment.vsg]]`` in bench TOML (``vsg_id``,
``resource``, optional ``model`` and ``driver``; default driver is VISA/SCPI).
Unsupported operations on a given ``model`` raise
:class:`~colosseum_equipment.exceptions.EquipmentCapabilityError`.
"""

from __future__ import annotations

from colosseum.decorators import command, measurement

from colosseum_equipment.api._verify import tolerance_verifier
from colosseum_equipment.connections import get_cached_instrument


@command
def set_frequency(*, vsg_id: int, frequency: float) -> None:
    """Set CW output frequency in hertz.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param frequency: Output frequency in hertz.
    :type frequency: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).set_frequency(frequency)


@command
def set_power(*, vsg_id: int, power_dbm: float) -> None:
    """Set output power in dBm.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param power_dbm: Output power in dBm.
    :type power_dbm: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).set_power(power_dbm)


@command
def set_output(*, vsg_id: int, enabled: bool) -> None:
    """Enable or disable RF output.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param enabled: ``True`` to enable RF output, ``False`` to disable.
    :type enabled: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).set_output(enabled)


@command
def preset(*, vsg_id: int) -> None:
    """Return the instrument to a default preset state.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).preset()


@command
def wait_complete(*, vsg_id: int) -> None:
    """Block until pending instrument operations complete (*OPC?*).

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).wait_complete()


@command
def set_alc(*, vsg_id: int, enabled: bool) -> None:
    """Enable or disable automatic level control (ALC).

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param enabled: ``True`` to enable ALC, ``False`` to disable.
    :type enabled: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).set_alc(enabled)


@command
def set_attenuation(*, vsg_id: int, attenuation_db: float) -> None:
    """Set output attenuation in dB.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param attenuation_db: Output attenuation in dB.
    :type attenuation_db: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).set_attenuation(attenuation_db)


@command
def set_phase(*, vsg_id: int, phase_deg: float) -> None:
    """Set RF phase in degrees (vector models).

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param phase_deg: RF phase in degrees.
    :type phase_deg: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).set_phase(phase_deg)


@command
def set_output_blanking(*, vsg_id: int, enabled: bool) -> None:
    """Enable or disable output blanking.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param enabled: ``True`` to enable output blanking, ``False`` to disable.
    :type enabled: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).set_output_blanking(enabled)


@command
def upload_waveform(
    *,
    vsg_id: int,
    local_path: str,
    remote_name: str,
    first_last_blanking: bool = False,
) -> None:
    """Upload an IQ or arb waveform ``.bin`` file to instrument memory.

    Uses SCPI binary block over TCPIP when available; otherwise FTP to the instrument.
    Set ``first_last_blanking=True`` to configure first/last-sample RF blanking
    for IQ loop playback.

    Requires a capable ``model`` (for example ``keysight-esg`` with E4438C IDN).

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param local_path: Path to the local ``.bin`` waveform file.
    :type local_path: str
    :param remote_name: Destination filename on the instrument.
    :type remote_name: str
    :param first_last_blanking: When True, configure first/last-sample RF blanking for IQ playback.
    :type first_last_blanking: bool, optional

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).upload_waveform(
        local_path,
        remote_name,
        first_last_blanking=first_last_blanking,
    )


@command
def delete_waveform(*, vsg_id: int, remote_name: str) -> None:
    """Delete a waveform and its associated marker/header files from instrument memory.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param remote_name: Waveform filename on the instrument to delete.
    :type remote_name: str

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).delete_waveform(remote_name)


@command
def delete_all_waveforms(*, vsg_id: int) -> None:
    """Delete all waveforms from volatile arb memory on the instrument.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).delete_all_waveforms()


@command
def set_multicarrier(*, vsg_id: int, num_tones: int, spacing_hz: float) -> None:
    """Configure multicarrier tone count and frequency spacing in hertz.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param num_tones: Number of carrier tones.
    :type num_tones: int
    :param spacing_hz: Frequency spacing between tones in hertz.
    :type spacing_hz: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).set_multicarrier(num_tones, spacing_hz)


@command
def toggle_multitone(*, vsg_id: int, enabled: bool) -> None:
    """Enable or disable multitone arbitrary waveform playback.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param enabled: ``True`` to enable multitone playback, ``False`` to disable.
    :type enabled: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).toggle_multitone(enabled)


@command
def play_iq(
    *,
    vsg_id: int,
    filename: str,
    center_freq_hz: float,
    amplitude_dbm: float,
    sample_clock_hz: float,
) -> None:
    """Select an uploaded IQ waveform and start playback at the given carrier and sample clock.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param filename: Uploaded waveform filename on the instrument.
    :type filename: str
    :param center_freq_hz: Carrier center frequency in hertz.
    :type center_freq_hz: float
    :param amplitude_dbm: Output amplitude in dBm.
    :type amplitude_dbm: float
    :param sample_clock_hz: IQ sample clock rate in hertz.
    :type sample_clock_hz: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).play_iq(
        filename,
        center_freq_hz,
        amplitude_dbm,
        sample_clock_hz,
    )


@command
def set_pulsegen_output(*, vsg_id: int, enabled: bool) -> None:
    """Enable or disable the internal pulse generator path (Keysight ``PULM:STAT``).

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param enabled: ``True`` to enable the pulse generator, ``False`` to disable.
    :type enabled: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).set_pulsegen_output(enabled)


@command
def set_pulsemod_output(*, vsg_id: int, enabled: bool) -> None:
    """Enable or disable pulse modulation.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param enabled: ``True`` to enable pulse modulation, ``False`` to disable.
    :type enabled: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).set_pulsemod_output(enabled)


@command
def set_pulse_period(*, vsg_id: int, period_s: float) -> None:
    """Set pulse period in seconds.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param period_s: Pulse period in seconds.
    :type period_s: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).set_pulse_period(period_s)


@command
def set_pulse_width(*, vsg_id: int, width_s: float) -> None:
    """Set pulse width in seconds.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param width_s: Pulse width in seconds.
    :type width_s: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).set_pulse_width(width_s)


@command
def pulse_source(*, vsg_id: int, source: str) -> None:
    """Set pulse source to ``PULSE``, ``SQUARE``, ``EXT1``, or ``EXT2``.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param source: Pulse source string accepted by the configured model.
    :type source: str

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).pulse_source(source)


@command
def step_power(
    *,
    vsg_id: int,
    start_dbm: float,
    stop_dbm: float,
    step_db: float,
    interval_s: float,
) -> None:
    """Run a stepped power sweep with the given start, stop, step size, and dwell interval.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param start_dbm: Starting power in dBm.
    :type start_dbm: float
    :param stop_dbm: Stopping power in dBm.
    :type stop_dbm: float
    :param step_db: Power step size in dB.
    :type step_db: float
    :param interval_s: Dwell time at each step in seconds.
    :type interval_s: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).step_power(start_dbm, stop_dbm, step_db, interval_s)


@command
def freq_sweep(
    *,
    vsg_id: int,
    start_hz: float,
    stop_hz: float,
    points: int,
    dwell_s: float,
) -> None:
    """Run a stepped frequency sweep.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param start_hz: Starting frequency in hertz.
    :type start_hz: float
    :param stop_hz: Stopping frequency in hertz.
    :type stop_hz: float
    :param points: Number of frequency steps.
    :type points: int
    :param dwell_s: Dwell time at each step in seconds.
    :type dwell_s: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).freq_sweep(start_hz, stop_hz, points, dwell_s)


@command
def amplitude_sweep(
    *,
    vsg_id: int,
    start_dbm: float,
    stop_dbm: float,
    points: int,
    dwell_s: float,
) -> None:
    """Run a stepped amplitude sweep.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param start_dbm: Starting amplitude in dBm.
    :type start_dbm: float
    :param stop_dbm: Stopping amplitude in dBm.
    :type stop_dbm: float
    :param points: Number of amplitude steps.
    :type points: int
    :param dwell_s: Dwell time at each step in seconds.
    :type dwell_s: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).amplitude_sweep(start_dbm, stop_dbm, points, dwell_s)


@command
def select_waveform(*, vsg_id: int, remote_name: str) -> None:
    """Select a waveform previously stored on the instrument.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param remote_name: Waveform filename on the instrument to select.
    :type remote_name: str

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).select_waveform(remote_name)


@command
def set_arb_state(*, vsg_id: int, enabled: bool) -> None:
    """Enable or disable arbitrary waveform generator playback.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param enabled: ``True`` to enable arb playback, ``False`` to disable.
    :type enabled: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).set_arb_state(enabled)


@command
def configure_list(
    *,
    vsg_id: int,
    frequencies: list[float],
    powers: list[float] | None = None,
) -> None:
    """Program a frequency (and optional power) list sweep.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param frequencies: List of sweep frequencies in hertz.
    :type frequencies: list[float]
    :param powers: Optional list of output powers in dBm, one per frequency.
    :type powers: list[float] | None, optional

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).configure_list(frequencies, powers)


@command
def set_modulation(*, vsg_id: int, enabled: bool, modulation_type: str = "none") -> None:
    """Enable modulation and set modulation type (model-specific strings).

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param enabled: ``True`` to enable modulation, ``False`` to disable.
    :type enabled: bool
    :param modulation_type: Modulation type string accepted by the configured model.
    :type modulation_type: str, optional

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("vsg", vsg_id).set_modulation(enabled, modulation_type)


@measurement
def measure_output_state(*, vsg_id: int, key: str) -> float:
    """Read whether RF output is enabled.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured state as ``1.0`` (on) or ``0.0`` (off).
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    enabled = get_cached_instrument("vsg", vsg_id).measure_output_state()
    return 1.0 if enabled else 0.0


verify_output_state = tolerance_verifier(
    "measure_output_state",
    name="verify_output_state",
    default_tolerance=0.0,
)


@measurement
def measure_frequency(*, vsg_id: int, key: str) -> float:
    """Read CW output frequency.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured frequency in hertz.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("vsg", vsg_id).measure_frequency())


verify_frequency = tolerance_verifier(
    "measure_frequency",
    name="verify_frequency",
    default_tolerance=1.0,
)


@measurement
def measure_power_dbm(*, vsg_id: int, key: str) -> float:
    """Read output power.

    :param vsg_id: Configured ``equipment.vsg`` id from bench TOML.
    :type vsg_id: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured power in dBm.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("vsg", vsg_id).measure_power_dbm())


verify_power_dbm = tolerance_verifier(
    "measure_power_dbm",
    name="verify_power_dbm",
    default_tolerance=0.5,
)
