"""Bench power supply APIs (``col.equipment.psu``)."""

from __future__ import annotations

from colosseum.decorators import command, measurement

from colosseum_equipment.api._verify import tolerance_verifier
from colosseum_equipment.connections import get_cached_instrument


@command
def set_voltage(*, psu_id: int, voltage: float) -> None:
    """Set the programmed output voltage.

    :param psu_id: Configured ``equipment.psu`` id from bench TOML.
    :type psu_id: int
    :param voltage: Target voltage in volts.
    :type voltage: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("psu", psu_id).set_voltage(voltage)


@command
def set_current_limit(*, psu_id: int, current: float) -> None:
    """Set the current limit.

    :param psu_id: Configured ``equipment.psu`` id from bench TOML.
    :type psu_id: int
    :param current: Current limit in amperes.
    :type current: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("psu", psu_id).set_current_limit(current)


@command
def set_output(*, psu_id: int, enabled: bool) -> None:
    """Enable or disable the output.

    :param psu_id: Configured ``equipment.psu`` id from bench TOML.
    :type psu_id: int
    :param enabled: ``True`` to enable output, ``False`` to disable.
    :type enabled: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("psu", psu_id).set_output(enabled)


@command
def wait_for_current(
    *,
    psu_id: int,
    current: float,
    timeout_s: float,
    tolerance: float = 0.01,
) -> None:
    """Block until measured output current reaches the target within tolerance.

    :param psu_id: Configured ``equipment.psu`` id from bench TOML.
    :type psu_id: int
    :param current: Target current in amperes.
    :type current: float
    :param timeout_s: Maximum wait time in seconds.
    :type timeout_s: float
    :param tolerance: Allowed absolute deviation in amperes.
    :type tolerance: float, optional

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("psu", psu_id).wait_for_current(
        current,
        timeout_s=timeout_s,
        tolerance=tolerance,
    )


@measurement
def measure_voltage(*, psu_id: int, key: str) -> float:
    """Read output voltage.

    :param psu_id: Configured ``equipment.psu`` id from bench TOML.
    :type psu_id: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured voltage in volts.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("psu", psu_id).measure_voltage())


verify_voltage = tolerance_verifier("measure_voltage", name="verify_voltage", unit="V")


@measurement
def measure_current(*, psu_id: int, key: str) -> float:
    """Read output current.

    :param psu_id: Configured ``equipment.psu`` id from bench TOML.
    :type psu_id: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured current in amperes.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("psu", psu_id).measure_current())


verify_current = tolerance_verifier("measure_current", name="verify_current", unit="A")


@measurement
def measure_output_state(*, psu_id: int, key: str) -> float:
    """Read whether output is enabled.

    :param psu_id: Configured ``equipment.psu`` id from bench TOML.
    :type psu_id: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured state as ``1.0`` (on) or ``0.0`` (off).
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    enabled = get_cached_instrument("psu", psu_id).measure_output_state()
    return 1.0 if enabled else 0.0


verify_output_state = tolerance_verifier(
    "measure_output_state",
    name="verify_output_state",
    default_tolerance=0.0,
)
