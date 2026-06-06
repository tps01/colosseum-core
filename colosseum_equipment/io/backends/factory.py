from __future__ import annotations

from typing import Any

from colosseum_equipment.io.backends.sim.dio import SimDioBackend
from colosseum_equipment.io.exceptions import IoConfigError, IoNotImplementedError

_DIO_VENDOR_DOC = "NI 6501/6502 DIO"
_I2C_VENDOR_DOC = "NI USB-845x I2C"
_SPI_VENDOR_DOC = "NI USB-845x SPI"


def _driver_name(config: dict[str, Any]) -> str:
    driver = config.get("driver")
    if driver in (None, ""):
        return "stub"
    return str(driver)


def _port_lines(config: dict[str, Any]) -> int:
    raw = config.get("port_lines", 8)
    return int(raw)


def _direction(config: dict[str, Any]) -> int:
    raw = config.get("direction", 0)
    if raw in (None, ""):
        return 0
    return int(raw)


def _require_driver(driver: str, operation: str, *, kind: str, vendor_doc: str) -> None:
    if driver in ("stub",):
        raise IoNotImplementedError(
            f"col.io {operation} requires driver documentation ({vendor_doc}); "
            f"configure driver= in bench TOML once implemented."
        )
    if kind == "dio" and driver == "ni-6501":
        raise IoNotImplementedError(
            f"col.io {operation}: driver `{driver}` is reserved; provide NI programming "
            f"documentation to implement ({vendor_doc})."
        )
    if kind in ("i2c", "spi") and driver == "ni-845x":
        raise IoNotImplementedError(
            f"col.io {operation}: driver `{driver}` is reserved; provide NI programming "
            f"documentation to implement ({vendor_doc})."
        )
    raise IoNotImplementedError(f"col.io {operation}: unsupported driver `{driver}`")


def open_dio_backend(dio_id: int, config: dict[str, Any]) -> Any:  # noqa: ANN401
    driver = _driver_name(config)
    if driver == "sim":
        return SimDioBackend.from_cache(
            dio_id=dio_id,
            port_lines=_port_lines(config),
            direction=_direction(config),
        )
    if driver == "ftdi-ft232h":
        from colosseum_equipment.io.backends.ftdi.dio import FtdiFt232hDioBackend

        return FtdiFt232hDioBackend(
            resource=str(config.get("resource") or ""),
            port_lines=_port_lines(config),
            direction=_direction(config),
        )
    _require_driver(driver, "dio", kind="dio", vendor_doc=_DIO_VENDOR_DOC)
    return None


class _StubBusBackend:
    def __init__(
        self, resource_id: int, config: dict[str, Any], *, kind: str, vendor_doc: str
    ) -> None:
        self._resource_id = resource_id
        self._config = config
        self._kind = kind
        self._vendor_doc = vendor_doc

    def _fail(self, operation: str) -> None:
        _require_driver(
            _driver_name(self._config), operation, kind=self._kind, vendor_doc=self._vendor_doc
        )

    def close(self) -> None:
        return None


class _StubI2cBackend(_StubBusBackend):
    def __init__(self, bus_id: int, config: dict[str, Any]) -> None:
        super().__init__(bus_id, config, kind="i2c", vendor_doc=_I2C_VENDOR_DOC)

    def write(self, address: int, data: bytes) -> None:
        _ = address, data
        self._fail("write")

    def read(self, address: int, length: int) -> bytes:
        _ = address, length
        self._fail("read")
        return b""

    def write_read(self, address: int, write_data: bytes, read_length: int) -> bytes:
        _ = address, write_data, read_length
        self._fail("write_read")
        return b""


class _StubSpiBackend(_StubBusBackend):
    def __init__(self, bus_id: int, config: dict[str, Any]) -> None:
        super().__init__(bus_id, config, kind="spi", vendor_doc=_SPI_VENDOR_DOC)

    def write(self, data: bytes) -> None:
        _ = data
        self._fail("write")

    def read(self, length: int) -> bytes:
        _ = length
        self._fail("read")
        return b""

    def transfer(self, write_data: bytes, read_length: int) -> bytes:
        _ = write_data, read_length
        self._fail("transfer")
        return b""


def open_i2c_backend(bus_id: int, config: dict[str, Any]) -> _StubI2cBackend:
    driver = _driver_name(config)
    if driver == "sim":
        raise IoNotImplementedError(
            "col.io i2c write: driver `sim` is not implemented; use driver=ni-845x when available."
        )
    return _StubI2cBackend(bus_id, config)


def open_spi_backend(bus_id: int, config: dict[str, Any]) -> _StubSpiBackend:
    driver = _driver_name(config)
    if driver == "sim":
        raise IoNotImplementedError(
            "col.io spi write: driver `sim` is not implemented; use driver=ni-845x when available."
        )
    return _StubSpiBackend(bus_id, config)


def open_backend(kind: str, resource_id: int, config: dict[str, Any]) -> Any:  # noqa: ANN401
    if kind == "dio":
        return open_dio_backend(resource_id, config)
    if kind == "i2c":
        return open_i2c_backend(resource_id, config)
    if kind == "spi":
        return open_spi_backend(resource_id, config)
    raise IoConfigError(f"unsupported io kind `{kind}`")
