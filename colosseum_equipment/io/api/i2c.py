from __future__ import annotations

from colosseum.config.loader import ConfigError
from colosseum.context import get_context

from colosseum_equipment.io.api._stub import require_driver


def _i2c_driver(bus_id: int) -> str | None:
    ctx = get_context()
    if ctx is None or ctx.config is None:
        return None
    try:
        return ctx.config.get_item("io.i2c", bus_id).get("driver")
    except ConfigError:
        return None


def write(*, bus_id: int, address: int, data: bytes) -> None:
    _ = address, data
    require_driver(_i2c_driver(bus_id), "write", vendor_doc="NI USB-845x I2C")


def read(*, bus_id: int, address: int, length: int) -> bytes:
    _ = address, length
    require_driver(_i2c_driver(bus_id), "read", vendor_doc="NI USB-845x I2C")
    return b""


def write_read(*, bus_id: int, address: int, write_data: bytes, read_length: int) -> bytes:
    _ = address, write_data, read_length
    require_driver(_i2c_driver(bus_id), "write_read", vendor_doc="NI USB-845x I2C")
    return b""
