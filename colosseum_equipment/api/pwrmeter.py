"""RF power meter APIs (``col.equipment.pwrmeter``)."""

from __future__ import annotations

from colosseum.decorators import command, measurement

from colosseum_equipment.api._verify import tolerance_verifier
from colosseum_equipment.connections import get_cached_instrument


@command
def set_frequency(*, pwrmeter_id: int, frequency_hz: float) -> None:
    """Set the calibration frequency.

    :param pwrmeter_id: Configured ``equipment.pwrmeter`` id from bench TOML.
    :type pwrmeter_id: int
    :param frequency_hz: Frequency in hertz.
    :type frequency_hz: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("pwrmeter", pwrmeter_id).set_frequency(frequency_hz)


@command
def set_averaging_count(*, pwrmeter_id: int, count: int) -> None:
    """Set the measurement averaging count.

    :param pwrmeter_id: Configured ``equipment.pwrmeter`` id from bench TOML.
    :type pwrmeter_id: int
    :param count: Number of averages.
    :type count: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("pwrmeter", pwrmeter_id).set_averaging_count(count)


@command
def zero_sensor(*, pwrmeter_id: int) -> None:
    """Zero the sensor.

    :param pwrmeter_id: Configured ``equipment.pwrmeter`` id from bench TOML.
    :type pwrmeter_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("pwrmeter", pwrmeter_id).zero_sensor()


@command
def preset(*, pwrmeter_id: int) -> None:
    """Return the instrument to a default preset.

    :param pwrmeter_id: Configured ``equipment.pwrmeter`` id from bench TOML.
    :type pwrmeter_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("pwrmeter", pwrmeter_id).preset()


@measurement
def measure_power(*, pwrmeter_id: int, key: str) -> float:
    """Measure RF power.

    :param pwrmeter_id: Configured ``equipment.pwrmeter`` id from bench TOML.
    :type pwrmeter_id: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured power in dBm.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("pwrmeter", pwrmeter_id).measure_power())


verify_power = tolerance_verifier(
    "measure_power", name="verify_power", default_tolerance=0.5, unit="dBm"
)
