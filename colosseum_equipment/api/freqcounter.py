"""Frequency counter APIs (``col.equipment.freqcounter``)."""

from __future__ import annotations

from colosseum.decorators import command, measurement

from colosseum_equipment.api._verify import tolerance_verifier
from colosseum_equipment.connections import get_cached_instrument


@command
def set_gate_time(*, freqcounter_id: int, seconds: float) -> None:
    """Set the measurement gate time.

    :param freqcounter_id: Configured ``equipment.freqcounter`` id from bench TOML.
    :type freqcounter_id: int
    :param seconds: Gate time in seconds.
    :type seconds: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("freqcounter", freqcounter_id).set_gate_time(seconds)


@command
def preset(*, freqcounter_id: int) -> None:
    """Return the instrument to a default preset.

    :param freqcounter_id: Configured ``equipment.freqcounter`` id from bench TOML.
    :type freqcounter_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("freqcounter", freqcounter_id).preset()


@measurement
def measure_frequency(*, freqcounter_id: int, key: str) -> float:
    """Measure input frequency.

    :param freqcounter_id: Configured ``equipment.freqcounter`` id from bench TOML.
    :type freqcounter_id: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured frequency in hertz.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("freqcounter", freqcounter_id).measure_frequency())


verify_frequency = tolerance_verifier(
    "measure_frequency",
    name="verify_frequency",
    default_tolerance=1.0,
    unit="Hz",
)


@measurement
def measure_period(*, freqcounter_id: int, key: str) -> float:
    """Measure input period.

    :param freqcounter_id: Configured ``equipment.freqcounter`` id from bench TOML.
    :type freqcounter_id: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured period in seconds.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("freqcounter", freqcounter_id).measure_period())
