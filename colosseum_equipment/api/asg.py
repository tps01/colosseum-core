"""Analog signal generator APIs exposed as ``col.equipment.asg``.

Configure instruments with ``[[equipment.asg]]`` in bench TOML (``asg_id``, ``resource``,
optional ``model`` and ``driver``; default driver is VISA/SCPI). Pulse generator and modulation
commands use R&S-style SCPI on the ``generic`` model.
"""

from __future__ import annotations

from colosseum.decorators import command

from colosseum_equipment.connections import get_cached_instrument


@command
def set_frequency(*, asg_id: int, frequency: float) -> None:
    """Set CW output frequency in hertz.

    :param asg_id: Configured ``equipment.asg`` id from bench TOML.
    :type asg_id: int
    :param frequency: Output frequency in hertz.
    :type frequency: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("asg", asg_id).set_frequency(frequency)


@command
def set_power(*, asg_id: int, power_dbm: float) -> None:
    """Set output power in dBm.

    :param asg_id: Configured ``equipment.asg`` id from bench TOML.
    :type asg_id: int
    :param power_dbm: Output power in dBm.
    :type power_dbm: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("asg", asg_id).set_power(power_dbm)


@command
def set_output(*, asg_id: int, enabled: bool) -> None:
    """Enable or disable RF output.

    :param asg_id: Configured ``equipment.asg`` id from bench TOML.
    :type asg_id: int
    :param enabled: ``True`` to enable RF output, ``False`` to disable.
    :type enabled: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("asg", asg_id).set_output(enabled)


@command
def set_pulsegen_output(*, asg_id: int, enabled: bool) -> None:
    """Enable or disable the pulse generator output (R&S-style).

    :param asg_id: Configured ``equipment.asg`` id from bench TOML.
    :type asg_id: int
    :param enabled: ``True`` to enable pulse generator output, ``False`` to disable.
    :type enabled: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("asg", asg_id).set_pulsegen_output(enabled)


@command
def set_pulsemod_output(*, asg_id: int, enabled: bool) -> None:
    """Enable or disable pulse modulation.

    :param asg_id: Configured ``equipment.asg`` id from bench TOML.
    :type asg_id: int
    :param enabled: ``True`` to enable pulse modulation, ``False`` to disable.
    :type enabled: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("asg", asg_id).set_pulsemod_output(enabled)


@command
def set_pulse_period(*, asg_id: int, period_s: float) -> None:
    """Set pulse period in seconds.

    :param asg_id: Configured ``equipment.asg`` id from bench TOML.
    :type asg_id: int
    :param period_s: Pulse period in seconds.
    :type period_s: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("asg", asg_id).set_pulse_period(period_s)


@command
def set_pulse_width(*, asg_id: int, width_s: float) -> None:
    """Set pulse width in seconds.

    :param asg_id: Configured ``equipment.asg`` id from bench TOML.
    :type asg_id: int
    :param width_s: Pulse width in seconds.
    :type width_s: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("asg", asg_id).set_pulse_width(width_s)
