from __future__ import annotations

from colosseum_equipment.io.exceptions import IoConfigError, IoConnectionError

try:
    from pyftdi.gpio import GpioMpsseController
except ImportError:  # pragma: no cover - exercised via missing-extra test
    GpioMpsseController = None  # type: ignore[misc, assignment]


def _line_mask(port_lines: int) -> int:
    if port_lines not in (8, 16):
        raise IoConfigError("ftdi-ft232h port_lines must be 8 (ADBUS) or 16 (ADBUS+ACBUS)")
    return (1 << port_lines) - 1


class FtdiFt232hDioBackend:
    """FT232H GPIO via pyftdi ``GpioMpsseController`` (MPSSE mode)."""

    def __init__(self, *, resource: str, port_lines: int, direction: int) -> None:
        if GpioMpsseController is None:
            raise IoConnectionError(
                "col.io ftdi-ft232h requires pyftdi; install with: pip install colosseum[io]"
            )
        if not resource:
            raise IoConfigError("ftdi-ft232h requires resource= (pyftdi URL, e.g. ftdi://ftdi:232h/1)")
        self._mask = _line_mask(port_lines)
        self._direction = direction & self._mask
        self._gpio = GpioMpsseController()
        try:
            self._gpio.configure(resource, direction=self._direction)
        except Exception as exc:
            raise IoConnectionError(f"failed to open FTDI GPIO at {resource!r}: {exc}") from exc

    def configure(self, direction: int) -> None:
        self._direction = direction & self._mask
        self._gpio.set_direction(self._mask, self._direction)

    def write_port(self, value: int) -> None:
        self._gpio.write(value & self._direction & self._mask)

    def read_port(self) -> int:
        return int(self._gpio.read()) & self._mask

    def write_pin(self, line: int, value: bool) -> None:
        bit = 1 << line
        if not (self._direction & bit):
            raise IoConfigError(f"line {line} is not configured as output")
        current = self.read_port()
        if value:
            current |= bit
        else:
            current &= ~bit
        self.write_port(current)

    def read_pin(self, line: int) -> bool:
        return bool(self.read_port() & (1 << line))

    def close(self) -> None:
        close = getattr(self._gpio, "close", None)
        if callable(close):
            close()
