from __future__ import annotations

from colosseum.config.loader import ConfigError
from colosseum.context import get_context

from colosseum_equipment.io.api._stub import require_driver


def _dio_driver(dio_id: int) -> str | None:
    ctx = get_context()
    if ctx is None or ctx.config is None:
        return None
    try:
        return ctx.config.get_item("io.dio", dio_id).get("driver")
    except ConfigError:
        return None


def write_pin(*, dio_id: int, line: int, value: bool) -> None:
    _ = line, value
    require_driver(_dio_driver(dio_id), "write_pin", vendor_doc="NI 6501/6502 DIO")


def read_pin(*, dio_id: int, line: int) -> bool:
    _ = line
    require_driver(_dio_driver(dio_id), "read_pin", vendor_doc="NI 6501/6502 DIO")
    return False
