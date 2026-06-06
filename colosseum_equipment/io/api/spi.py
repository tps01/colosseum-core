"""Reserved SPI bus APIs (``col.io.spi``).

The namespace is exposed for compatibility, but NI USB-845x support is not
implemented yet. Calls fail immediately with ``IoNotImplementedError``.
"""

from __future__ import annotations

from colosseum.decorators import command

from colosseum_equipment.io.connections import get_backend


@command
def write(*, bus_id: int, data: bytes) -> None:
    """Write bytes on SPI.

    :param bus_id: Configured ``io.spi`` id from bench TOML.
    :type bus_id: int
    :param data: Payload bytes.
    :type data: bytes

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_backend("spi", bus_id).write(data)


@command
def read(*, bus_id: int, length: int) -> bytes:
    """Read bytes on SPI.

    :param bus_id: Configured ``io.spi`` id from bench TOML.
    :type bus_id: int
    :param length: Number of bytes to read.
    :type length: int

    :returns: Payload bytes.
    :rtype: bytes

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    return bytes(get_backend("spi", bus_id).read(length))


@command
def transfer(*, bus_id: int, write_data: bytes, read_length: int) -> bytes:
    """Full-duplex SPI transfer.

    :param bus_id: Configured ``io.spi`` id from bench TOML.
    :type bus_id: int
    :param write_data: Bytes to clock out.
    :type write_data: bytes
    :param read_length: Number of bytes to read.
    :type read_length: int

    :returns: Bytes read during the transfer.
    :rtype: bytes

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    return bytes(get_backend("spi", bus_id).transfer(write_data, read_length))
