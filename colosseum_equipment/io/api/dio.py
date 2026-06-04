from __future__ import annotations

from colosseum.decorators import measurement

from colosseum_equipment.io.connections import get_backend


def configure(*, dio_id: int, direction: int) -> None:
    get_backend("dio", dio_id).configure(direction)


def write_port(*, dio_id: int, value: int) -> None:
    get_backend("dio", dio_id).write_port(value)


@measurement
def read_port(*, dio_id: int, key: str) -> int:
    return get_backend("dio", dio_id).read_port()


def write_pin(*, dio_id: int, line: int, value: bool) -> None:
    get_backend("dio", dio_id).write_pin(line, value)


@measurement
def read_pin(*, dio_id: int, line: int, key: str) -> bool:
    return get_backend("dio", dio_id).read_pin(line)
