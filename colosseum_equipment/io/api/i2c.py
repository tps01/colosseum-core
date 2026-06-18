"""Reserved I2C bus APIs (``col.io.i2c``).

The namespace is exposed for compatibility, but NI USB-845x support is not
implemented yet. Calls fail immediately with ``IoNotImplementedError``.
"""

from __future__ import annotations

from colosseum.decorators import command

from colosseum_equipment.io.connections import get_backend


@command
def write(*, bus_id: int, address: int, data: bytes) -> None:
    """Write bytes to an I2C device.

    :param bus_id: Configured ``io.i2c`` id from bench TOML.
    :type bus_id: int
    :param address: 7-bit device address.
    :type address: int
    :param data: Payload bytes.
    :type data: bytes

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_backend("i2c", bus_id).write(address, data)


@command
def read(*, bus_id: int, address: int, length: int) -> bytes:
    """Read bytes from an I2C device.

    :param bus_id: Configured ``io.i2c`` id from bench TOML.
    :type bus_id: int
    :param address: 7-bit device address.
    :type address: int
    :param length: Number of bytes to read.
    :type length: int

    :returns: Payload bytes.
    :rtype: bytes

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    return bytes(get_backend("i2c", bus_id).read(address, length))


@command
def write_read(*, bus_id: int, address: int, write_data: bytes, read_length: int) -> bytes:
    """Write then read on an I2C device.

    :param bus_id: Configured ``io.i2c`` id from bench TOML.
    :type bus_id: int
    :param address: 7-bit device address.
    :type address: int
    :param write_data: Bytes to write before the read.
    :type write_data: bytes
    :param read_length: Number of bytes to read.
    :type read_length: int

    :returns: Bytes read from the device.
    :rtype: bytes

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    return bytes(get_backend("i2c", bus_id).write_read(address, write_data, read_length))
