"""High-level vector/signal generator APIs exposed as ``col.equipment.vsg``.

Configure instruments with ``[[equipment.vsg]]`` in bench TOML (``vsg_id``, ``resource``,
optional ``model`` and ``driver``; default driver is VISA/SCPI). Unsupported operations on a given ``model`` raise
:class:`~colosseum_equipment.exceptions.EquipmentCapabilityError`.
"""

from __future__ import annotations

from colosseum.decorators import MeasurementSource, VerificationResult, measurement, verification

from colosseum_equipment.api._verify import verify_tolerance
from colosseum_equipment.connections import get_cached_instrument


def set_frequency(*, vsg_id: int, frequency: float) -> None:
    """Set CW output frequency in hertz."""
    get_cached_instrument("vsg", vsg_id).set_frequency(frequency)


def set_power(*, vsg_id: int, power_dbm: float) -> None:
    """Set output power in dBm."""
    get_cached_instrument("vsg", vsg_id).set_power(power_dbm)


def set_output(*, vsg_id: int, enabled: bool) -> None:
    """Enable or disable RF output."""
    get_cached_instrument("vsg", vsg_id).set_output(enabled)


def preset(*, vsg_id: int) -> None:
    """Return the instrument to a default preset state."""
    get_cached_instrument("vsg", vsg_id).preset()


def wait_complete(*, vsg_id: int) -> None:
    """Block until pending instrument operations complete (*OPC?*)."""
    get_cached_instrument("vsg", vsg_id).wait_complete()


def set_alc(*, vsg_id: int, enabled: bool) -> None:
    """Enable or disable automatic level control (ALC)."""
    get_cached_instrument("vsg", vsg_id).set_alc(enabled)


def set_attenuation(*, vsg_id: int, attenuation_db: float) -> None:
    """Set output attenuation in dB."""
    get_cached_instrument("vsg", vsg_id).set_attenuation(attenuation_db)


def set_phase(*, vsg_id: int, phase_deg: float) -> None:
    """Set RF phase in degrees (vector models)."""
    get_cached_instrument("vsg", vsg_id).set_phase(phase_deg)


def set_output_blanking(*, vsg_id: int, enabled: bool) -> None:
    """Enable or disable output blanking."""
    get_cached_instrument("vsg", vsg_id).set_output_blanking(enabled)


def upload_waveform(*, vsg_id: int, local_path: str, remote_name: str) -> None:
    """Upload an IQ or arb waveform file to instrument memory.

    Requires a capable ``model`` (for example ``keysight-esg`` with E4438C IDN).
    """
    get_cached_instrument("vsg", vsg_id).upload_waveform(local_path, remote_name)


def select_waveform(*, vsg_id: int, remote_name: str) -> None:
    """Select a waveform previously stored on the instrument."""
    get_cached_instrument("vsg", vsg_id).select_waveform(remote_name)


def set_arb_state(*, vsg_id: int, enabled: bool) -> None:
    """Enable or disable arbitrary waveform generator playback."""
    get_cached_instrument("vsg", vsg_id).set_arb_state(enabled)


def configure_list(
    *,
    vsg_id: int,
    frequencies: list[float],
    powers: list[float] | None = None,
) -> None:
    """Program a frequency (and optional power) list sweep."""
    get_cached_instrument("vsg", vsg_id).configure_list(frequencies, powers)


def set_modulation(*, vsg_id: int, enabled: bool, modulation_type: str = "none") -> None:
    """Enable modulation and set modulation type (model-specific strings)."""
    get_cached_instrument("vsg", vsg_id).set_modulation(enabled, modulation_type)


@measurement
def measure_output_state(*, vsg_id: int, key: str) -> float:
    """Record whether RF output is enabled (1.0) or disabled (0.0)."""
    enabled = get_cached_instrument("vsg", vsg_id).measure_output_state()
    return 1.0 if enabled else 0.0


@verification(sources=[MeasurementSource(domain="equipment", command="measure_output_state")])
def verify_output_state(
    *,
    key: str,
    expected_val: float,
    tolerance: float = 0.0,
    optional: bool = False,
) -> VerificationResult:
    return verify_tolerance(
        domain="equipment",
        command="measure_output_state",
        key=key,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )


@measurement
def measure_frequency(*, vsg_id: int, key: str) -> float:
    return get_cached_instrument("vsg", vsg_id).measure_frequency()


@verification(sources=[MeasurementSource(domain="equipment", command="measure_frequency")])
def verify_frequency(
    *,
    key: str,
    expected_val: float,
    tolerance: float = 1.0,
    optional: bool = False,
) -> VerificationResult:
    return verify_tolerance(
        domain="equipment",
        command="measure_frequency",
        key=key,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )


@measurement
def measure_power_dbm(*, vsg_id: int, key: str) -> float:
    return get_cached_instrument("vsg", vsg_id).measure_power_dbm()


@verification(sources=[MeasurementSource(domain="equipment", command="measure_power_dbm")])
def verify_power_dbm(
    *,
    key: str,
    expected_val: float,
    tolerance: float = 0.5,
    optional: bool = False,
) -> VerificationResult:
    return verify_tolerance(
        domain="equipment",
        command="measure_power_dbm",
        key=key,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )
