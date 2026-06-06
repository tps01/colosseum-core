"""Shared test doubles for equipment transports."""

from __future__ import annotations


class StubTransport:
    def write(self, data: str) -> None:
        pass

    def query(self, data: str) -> str:
        return "0"

    def close(self) -> None:
        pass


class RfStubTransport(StubTransport):
    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self._responses = responses or {}
        self.written: list[str] = []
        self.raw_written: list[bytes] = []

    def write(self, data: str) -> None:
        self.written.append(data)

    def query(self, data: str) -> str:
        return self._responses.get(data.strip(), "0")

    def write_raw(self, data: bytes) -> None:
        self.raw_written.append(data)

    def read_raw(self, size: int = 655360) -> bytes:
        raw = self._responses.get("__raw__", b"#210000000000")
        if isinstance(raw, str):
            return raw.encode("ascii")
        return raw
