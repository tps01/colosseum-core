from __future__ import annotations

from colosseum_equipment.io.connections import get_backend


def write(*, bus_id: int, address: int, data: bytes) -> None:
    get_backend("i2c", bus_id).write(address, data)


def read(*, bus_id: int, address: int, length: int) -> bytes:
    return get_backend("i2c", bus_id).read(address, length)


def write_read(*, bus_id: int, address: int, write_data: bytes, read_length: int) -> bytes:
    return get_backend("i2c", bus_id).write_read(address, write_data, read_length)
