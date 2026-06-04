from __future__ import annotations

from colosseum_equipment.io.connections import get_backend


def write(*, bus_id: int, data: bytes) -> None:
    get_backend("spi", bus_id).write(data)


def read(*, bus_id: int, length: int) -> bytes:
    return get_backend("spi", bus_id).read(length)


def transfer(*, bus_id: int, write_data: bytes, read_length: int) -> bytes:
    return get_backend("spi", bus_id).transfer(write_data, read_length)
