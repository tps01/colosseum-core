"""Unit tests for equipment connection cache and shutdown."""

from __future__ import annotations

import logging

from colosseum_equipment.connections import _atexit_close_equipment, close_all


class _RecordingClose:
    def __init__(self, label: str, order: list[str]) -> None:
        self._label = label
        self._order = order

    def close(self) -> None:
        self._order.append(self._label)


class _SpecaStyleInstrument:
    """Instrument that writes on close before closing its transport."""

    def __init__(self, transport: _TransportWithWriteOnClose, order: list[str]) -> None:
        self._transport = transport
        self._order = order

    def close(self) -> None:
        self._order.append("instrument:pre_write")
        self._transport.write("DISP:UPD ON")
        self._order.append("instrument:close_transport")
        self._transport.close()


class _TransportWithWriteOnClose:
    def __init__(self, order: list[str]) -> None:
        self._order = order
        self.closed = False

    def write(self, data: str) -> None:
        if self.closed:
            raise RuntimeError("write on closed transport")
        self._order.append(f"transport:write:{data}")

    def close(self) -> None:
        self.closed = True
        self._order.append("transport:close")


def test_close_all_closes_instruments_before_transports(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    order: list[str] = []
    transport = _TransportWithWriteOnClose(order)
    instrument = _SpecaStyleInstrument(transport, order)

    ctx.resource_cache["equipment:speca:0"] = transport
    ctx.resource_cache["instrument:speca:0"] = instrument

    close_all()

    assert order == [
        "instrument:pre_write",
        "transport:write:DISP:UPD ON",
        "instrument:close_transport",
        "transport:close",
        "transport:close",
    ]
    assert ctx.resource_cache == {}


def test_close_all_transport_only_when_no_instrument(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    order: list[str] = []
    ctx.resource_cache["equipment:dmm:1"] = _RecordingClose("transport", order)

    close_all()

    assert order == ["transport"]
    assert ctx.resource_cache == {}


def test_close_all_delegates_io_backend_shutdown(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    order: list[str] = []
    ctx.resource_cache["io:backend:dio:1"] = _RecordingClose("io", order)
    ctx.resource_cache["equipment:dmm:1"] = _RecordingClose("transport", order)

    close_all()

    assert order == ["io", "transport"]
    assert ctx.resource_cache == {}


class _FailingClose:
    def close(self) -> None:
        raise RuntimeError("close failed")


def test_close_all_continues_after_close_failure(unit_runtime_context, caplog) -> None:
    ctx = unit_runtime_context
    order: list[str] = []
    ctx.resource_cache["instrument:psu:1"] = _FailingClose()
    ctx.resource_cache["equipment:dmm:1"] = _RecordingClose("dmm", order)

    with caplog.at_level(logging.ERROR, logger="colosseum.equipment"):
        close_all()

    assert order == ["dmm"]
    assert ctx.resource_cache == {}
    assert "Failed to close cached resource instrument:psu:1" in caplog.text


def test_atexit_close_equipment_closes_open_cache(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    order: list[str] = []
    ctx.resource_cache["equipment:psu:1"] = _RecordingClose("psu", order)

    _atexit_close_equipment()

    assert order == ["psu"]
    assert ctx.resource_cache == {}


def test_atexit_close_equipment_skips_when_finalized(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    order: list[str] = []
    ctx.finalized = True
    ctx.resource_cache["equipment:psu:1"] = _RecordingClose("psu", order)

    _atexit_close_equipment()

    assert order == []
    assert "equipment:psu:1" in ctx.resource_cache
