"""Experimental SDR APIs (``col.equipment.sdr``).

The namespace is reserved for compatibility. UHD-backed behavior remains deferred
until vendor documentation is available, and configured ``driver = stub`` surfaces
raise explicit capability errors when called.
"""

from __future__ import annotations

from colosseum.decorators import command

from colosseum_equipment.connections import get_cached_instrument


@command
def set_center_frequency(*, sdr_id: int, frequency_hz: float) -> None:
    """Set RF center frequency.

    :param sdr_id: Configured ``equipment.sdr`` id from bench TOML.
    :type sdr_id: int
    :param frequency_hz: Center frequency in hertz.
    :type frequency_hz: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("sdr", sdr_id).set_center_frequency(frequency_hz)


@command
def set_sample_rate(*, sdr_id: int, sample_rate: float) -> None:
    """Set IQ sample rate.

    :param sdr_id: Configured ``equipment.sdr`` id from bench TOML.
    :type sdr_id: int
    :param sample_rate: Sample rate in samples per second.
    :type sample_rate: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("sdr", sdr_id).set_sample_rate(sample_rate)


@command
def set_gain(*, sdr_id: int, gain_db: float) -> None:
    """Set receiver gain.

    :param sdr_id: Configured ``equipment.sdr`` id from bench TOML.
    :type sdr_id: int
    :param gain_db: Gain in dB.
    :type gain_db: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("sdr", sdr_id).set_gain(gain_db)


@command
def capture_iq(*, sdr_id: int, path: str) -> None:
    """Capture IQ samples to a file under the run directory.

    :param sdr_id: Configured ``equipment.sdr`` id from bench TOML.
    :type sdr_id: int
    :param path: Relative path under the run directory.
    :type path: str

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("sdr", sdr_id).capture_iq(path)
