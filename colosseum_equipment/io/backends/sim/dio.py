from __future__ import annotations

from colosseum.context import require_context

from colosseum_equipment.io.exceptions import IoConfigError

_SIM_STATE_KEY = "io:sim:state"


def _line_mask(port_lines: int) -> int:
    if port_lines <= 0 or port_lines > 16:
        raise IoConfigError(f"port_lines must be 1..16, got {port_lines}")
    return (1 << port_lines) - 1


def _state_key(dio_id: int) -> str:
    return f"dio:{dio_id}"


class SimDioBackend:
    """In-memory GPIO for offline runs and unit tests."""

    def __init__(self, *, dio_id: int, port_lines: int, direction: int) -> None:
        mask = _line_mask(port_lines)
        self._dio_id = dio_id
        self._mask = mask
        self._direction = direction & mask
        self._output = 0
        self._input = 0

    def _persist(self) -> None:
        ctx = require_context()
        state = ctx.resource_cache.setdefault(_SIM_STATE_KEY, {})
        state[_state_key(self._dio_id)] = {
            "direction": self._direction,
            "output": self._output,
            "input": self._input,
            "mask": self._mask,
        }

    @classmethod
    def from_cache(cls, *, dio_id: int, port_lines: int, direction: int) -> SimDioBackend:
        ctx = require_context()
        state = ctx.resource_cache.setdefault(_SIM_STATE_KEY, {})
        key = _state_key(dio_id)
        mask = _line_mask(port_lines)
        if key not in state:
            backend = cls(dio_id=dio_id, port_lines=port_lines, direction=direction)
            backend._persist()
            return backend
        entry = state[key]
        backend = cls(dio_id=dio_id, port_lines=port_lines, direction=entry["direction"])
        backend._output = entry["output"] & mask
        backend._input = entry["input"] & mask
        backend._direction = entry["direction"] & mask
        return backend

    def configure(self, direction: int) -> None:
        self._direction = direction & self._mask
        self._persist()

    def write_port(self, value: int) -> None:
        self._output = value & self._direction & self._mask
        self._persist()

    def read_port(self) -> int:
        return ((self._output & self._direction) | (self._input & ~self._direction)) & self._mask

    def write_pin(self, line: int, value: bool) -> None:
        bit = 1 << line
        if line < 0 or line >= self._mask.bit_length():
            raise IoConfigError(
                f"line {line} out of range for port_lines={self._mask.bit_length()}"
            )
        if not (self._direction & bit):
            raise IoConfigError(f"line {line} is not configured as output")
        if value:
            self._output |= bit
        else:
            self._output &= ~bit
        self._output &= self._mask
        self._persist()

    def read_pin(self, line: int) -> bool:
        bit = 1 << line
        if line < 0 or line >= self._mask.bit_length():
            raise IoConfigError(
                f"line {line} out of range for port_lines={self._mask.bit_length()}"
            )
        return bool(self.read_port() & bit)

    def close(self) -> None:
        return None
