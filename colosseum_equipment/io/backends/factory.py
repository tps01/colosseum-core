from __future__ import annotations

from typing import Any

from colosseum_equipment.io.backends.sim.dio import SimDioBackend
from colosseum_equipment.io.exceptions import IoConfigError, IoNotImplementedError

_DIO_VENDOR_DOC = "NI 6501/6502 DIO"


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


def _require_dio_driver(driver: str, operation: str) -> None:
    if driver in ("stub",):
        raise IoNotImplementedError(
            f"col.io {operation} requires driver documentation ({_DIO_VENDOR_DOC}); "
            f"configure driver= in bench TOML once implemented."
        )
    if driver == "ni-6501":
        raise IoNotImplementedError(
            f"col.io {operation}: driver `{driver}` is reserved; provide NI programming "
            f"documentation to implement ({_DIO_VENDOR_DOC})."
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
    _require_dio_driver(driver, "dio")
    return None


def open_backend(kind: str, resource_id: int, config: dict[str, Any]) -> Any:  # noqa: ANN401
    if kind == "dio":
        return open_dio_backend(resource_id, config)
    raise IoConfigError(f"unsupported io kind `{kind}`")
