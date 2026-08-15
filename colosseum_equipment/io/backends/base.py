from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DioBackend(Protocol):
    """Digital I/O backend (single port or multi-line GPIO)."""

    def configure(self, direction: int) -> None:
        """Set line directions (1=output, 0=input)."""

    def write_port(self, value: int) -> None:
        """Write output lines in one call."""

    def read_port(self) -> int:
        """Read all configured lines."""

    def write_pin(self, line: int, value: bool) -> None:
        """Write one output line."""

    def read_pin(self, line: int) -> bool:
        """Read one line."""

    def close(self) -> None:
        """Release hardware resources."""
