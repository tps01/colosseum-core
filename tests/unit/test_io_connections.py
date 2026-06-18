"""IO connection cache and shutdown."""

from __future__ import annotations

from colosseum_equipment.io.connections import close_all


class _RecordingClose:
    def __init__(self, label: str, order: list[str]) -> None:
        self._label = label
        self._order = order

    def close(self) -> None:
        self._order.append(self._label)


def test_io_close_all_closes_backend_keys(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    order: list[str] = []
    ctx.resource_cache["io:backend:dio:1"] = _RecordingClose("dio", order)

    close_all()

    assert order == ["dio"]
    assert ctx.resource_cache == {}
