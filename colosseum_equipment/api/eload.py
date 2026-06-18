"""Electronic load APIs (``col.equipment.eload``)."""

from __future__ import annotations

from colosseum.decorators import command, measurement

from colosseum_equipment.api._verify import tolerance_verifier
from colosseum_equipment.connections import get_cached_instrument


@command
def set_mode(*, eload_id: int, mode: str) -> None:
    """Set operating mode (CC, CV, CP, or CR per model).

    :param eload_id: Configured ``equipment.eload`` id from bench TOML.
    :type eload_id: int
    :param mode: Mode string accepted by the configured model.
    :type mode: str

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("eload", eload_id).set_mode(mode)


@command
def set_current(*, eload_id: int, current: float) -> None:
    """Set constant-current level.

    :param eload_id: Configured ``equipment.eload`` id from bench TOML.
    :type eload_id: int
    :param current: Target current in amperes.
    :type current: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("eload", eload_id).set_current(current)


@command
def set_voltage(*, eload_id: int, voltage: float) -> None:
    """Set constant-voltage level.

    :param eload_id: Configured ``equipment.eload`` id from bench TOML.
    :type eload_id: int
    :param voltage: Target voltage in volts.
    :type voltage: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("eload", eload_id).set_voltage(voltage)


@command
def set_power(*, eload_id: int, power: float) -> None:
    """Set constant-power level (use when load is in CP mode).

    :param eload_id: Configured ``equipment.eload`` id from bench TOML.
    :type eload_id: int
    :param power: Target power in watts.
    :type power: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("eload", eload_id).set_power(power)


@command
def set_resistance(*, eload_id: int, resistance: float) -> None:
    """Set constant-resistance level (use when load is in CR mode).

    :param eload_id: Configured ``equipment.eload`` id from bench TOML.
    :type eload_id: int
    :param resistance: Target resistance in ohms.
    :type resistance: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("eload", eload_id).set_resistance(resistance)


@command
def engage(*, eload_id: int) -> None:
    """Connect the load input.

    :param eload_id: Configured ``equipment.eload`` id from bench TOML.
    :type eload_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("eload", eload_id).engage()


@command
def disengage(*, eload_id: int) -> None:
    """Disconnect the load input.

    :param eload_id: Configured ``equipment.eload`` id from bench TOML.
    :type eload_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("eload", eload_id).disengage()


@command
def preset(*, eload_id: int) -> None:
    """Return the instrument to a default preset.

    :param eload_id: Configured ``equipment.eload`` id from bench TOML.
    :type eload_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("eload", eload_id).preset()


@measurement
def measure_voltage(*, eload_id: int, key: str) -> float:
    """Read input voltage.

    :param eload_id: Configured ``equipment.eload`` id from bench TOML.
    :type eload_id: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured voltage in volts.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("eload", eload_id).measure_voltage())


verify_voltage = tolerance_verifier("measure_voltage", name="verify_voltage", unit="V")


@measurement
def measure_current(*, eload_id: int, key: str) -> float:
    """Read input current.

    :param eload_id: Configured ``equipment.eload`` id from bench TOML.
    :type eload_id: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured current in amperes.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("eload", eload_id).measure_current())


verify_current = tolerance_verifier("measure_current", name="verify_current", unit="A")
