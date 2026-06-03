from __future__ import annotations

from colosseum_equipment.transports.base import Transport


class NullTransport(Transport):
    """No-op transport for stub drivers (for example SDR API scaffolding)."""

    def write(self, data: str) -> None:
        _ = data

    def read(self) -> str:
        return ""

    def query(self, command: str) -> str:
        _ = command
        return ""

    def close(self) -> None:
        return None
