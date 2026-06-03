from __future__ import annotations

from colosseum.config.loader import ConfigError
from colosseum.context import get_context

from colosseum_equipment.io.api._stub import require_driver


def _spi_driver(bus_id: int) -> str | None:
    ctx = get_context()
    if ctx is None or ctx.config is None:
        return None
    try:
        return ctx.config.get_item("io.spi", bus_id).get("driver")
    except ConfigError:
        return None


def write(*, bus_id: int, data: bytes) -> None:
    _ = data
    require_driver(_spi_driver(bus_id), "write", vendor_doc="NI USB-845x SPI")


def read(*, bus_id: int, length: int) -> bytes:
    _ = length
    require_driver(_spi_driver(bus_id), "read", vendor_doc="NI USB-845x SPI")
    return b""


def transfer(*, bus_id: int, write_data: bytes, read_length: int) -> bytes:
    _ = write_data, read_length
    require_driver(_spi_driver(bus_id), "transfer", vendor_doc="NI USB-845x SPI")
    return b""
