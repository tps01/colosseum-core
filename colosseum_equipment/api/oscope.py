"""Oscilloscope APIs (``col.equipment.oscope``)."""

from __future__ import annotations

from colosseum.decorators import command, measurement

from colosseum_equipment.api._verify import tolerance_verifier
from colosseum_equipment.connections import get_cached_instrument


@command
def preset(*, oscope_id: int) -> None:
    """Return the scope to a default preset.

    :param oscope_id: Configured ``equipment.oscope`` id from bench TOML.
    :type oscope_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("oscope", oscope_id).preset()


@command
def set_timebase_scale(*, oscope_id: int, seconds_per_div: float) -> None:
    """Set horizontal timebase scale.

    :param oscope_id: Configured ``equipment.oscope`` id from bench TOML.
    :type oscope_id: int
    :param seconds_per_div: Seconds per division.
    :type seconds_per_div: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("oscope", oscope_id).set_timebase_scale(seconds_per_div)


@command
def single_acquire(*, oscope_id: int) -> None:
    """Run a single acquisition.

    :param oscope_id: Configured ``equipment.oscope`` id from bench TOML.
    :type oscope_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("oscope", oscope_id).single_acquire()


@measurement
def measure_vpp(*, oscope_id: int, channel: int = 1, key: str) -> float:
    """Measure peak-to-peak voltage.

    :param oscope_id: Configured ``equipment.oscope`` id from bench TOML.
    :type oscope_id: int
    :param channel: Scope channel number (default ``1``).
    :type channel: int, optional
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured voltage in volts.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("oscope", oscope_id).measure_vpp(channel))


verify_vpp = tolerance_verifier("measure_vpp", name="verify_vpp", unit="V")


@command
def save_screenshot(*, oscope_id: int, path: str) -> None:
    """Save a screen capture under the run directory.

    :param oscope_id: Configured ``equipment.oscope`` id from bench TOML.
    :type oscope_id: int
    :param path: Relative path under the run directory.
    :type path: str

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("oscope", oscope_id).save_screenshot(path)
