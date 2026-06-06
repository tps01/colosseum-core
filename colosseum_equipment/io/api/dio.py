"""Digital I/O APIs (``col.io.dio``). Measurements use domain ``equipment`` in SQLite."""

from __future__ import annotations

from colosseum.decorators import command, measurement

from colosseum_equipment.io.connections import get_backend


@command
def configure(*, dio_id: int, direction: int) -> None:
    """Configure port direction bitmask.

    :param dio_id: Configured ``equipment.dio`` id from bench TOML.
    :type dio_id: int
    :param direction: Bitmask of input (0) vs output (1) per line.
    :type direction: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_backend("dio", dio_id).configure(direction)


@command
def write_port(*, dio_id: int, value: int) -> None:
    """Write a port value.

    :param dio_id: Configured ``equipment.dio`` id from bench TOML.
    :type dio_id: int
    :param value: Port output bitmask.
    :type value: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_backend("dio", dio_id).write_port(value)


@measurement
def read_port(*, dio_id: int, key: str) -> int:
    """Read a full port value.

    :param dio_id: Configured ``equipment.dio`` id from bench TOML.
    :type dio_id: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured port bitmask as integer.
    :rtype: int

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return int(get_backend("dio", dio_id).read_port())


@command
def write_pin(*, dio_id: int, line: int, value: bool) -> None:
    """Write one GPIO line.

    :param dio_id: Configured ``equipment.dio`` id from bench TOML.
    :type dio_id: int
    :param line: Line index.
    :type line: int
    :param value: Line level.
    :type value: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_backend("dio", dio_id).write_pin(line, value)


@measurement
def read_pin(*, dio_id: int, line: int, key: str) -> bool:
    """Read one GPIO line.

    :param dio_id: Configured ``equipment.dio`` id from bench TOML.
    :type dio_id: int
    :param line: Line index.
    :type line: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured line level as bool.
    :rtype: bool

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return bool(get_backend("dio", dio_id).read_pin(line))
