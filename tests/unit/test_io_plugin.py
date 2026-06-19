from __future__ import annotations

import pytest

import colosseum as col
from colosseum.config import load_config
from colosseum.context import RuntimeContext
from colosseum_equipment.connections import close_all


def test_io_write_pin_without_config_records_command_error(io_runtime_context: RuntimeContext) -> None:
    ctx = io_runtime_context
    assert col.io.dio.write_pin(dio_id=1, line=0, value=True) is None
    row = ctx.db.fetch_table_rows("commands")[-1]
    assert row["status"] == "ERROR"
    assert ctx.result_aggregator.overall_pass() is False


def test_io_write_pin_stub_driver_records_command_error(
    io_runtime_context: RuntimeContext,
    io_bench,
) -> None:
    ctx = io_runtime_context
    load_config(
        io_bench(
            """
            [[io.dio]]
            dio_id = 1
            """,
        )
    )
    assert col.io.dio.write_pin(dio_id=1, line=0, value=True) is None
    row = ctx.db.fetch_table_rows("commands")[-1]
    assert row["status"] == "ERROR"
    assert "NI 6501" in (row["message"] or "")


def test_io_dio_sim_read_write_port(io_runtime_context: RuntimeContext, io_bench) -> None:
    load_config(
        io_bench(
            """
            [[io.dio]]
            dio_id = 1
            driver = sim
            port_lines = 8
            direction = 0xFF
            """,
        )
    )
    col.io.dio.write_port(dio_id=1, value=0b1010)
    assert col.io.dio.read_port(dio_id=1, key="port_a") == 0b1010
    col.io.dio.write_pin(dio_id=1, line=0, value=True)
    assert col.io.dio.read_pin(dio_id=1, line=0, key="line0") is True


def test_io_dio_sim_measurement_domain_equipment(io_runtime_context: RuntimeContext, io_bench) -> None:
    ctx = io_runtime_context
    load_config(
        io_bench(
            """
            [[io.dio]]
            dio_id = 1
            driver = sim
            port_lines = 8
            direction = 0xFF
            """,
        )
    )
    col.io.dio.write_port(dio_id=1, value=3)
    col.io.dio.read_port(dio_id=1, key="p1")
    rows = ctx.db.list_measurements(domain="equipment", command="io.dio.read_port", key="p1")
    assert len(rows) == 1
    assert rows[0].value == 3


def test_io_connections_close_all(io_runtime_context: RuntimeContext, io_bench) -> None:
    ctx = io_runtime_context
    load_config(
        io_bench(
            """
            [[io.dio]]
            dio_id = 1
            driver = sim
            port_lines = 8
            direction = 0xFF
            """,
        )
    )
    col.io.dio.write_port(dio_id=1, value=1)
    assert "io:backend:dio:1" in ctx.resource_cache
    close_all()
    assert "io:backend:dio:1" not in ctx.resource_cache


def test_io_ftdi_missing_extra_records_command_error(
    io_runtime_context: RuntimeContext,
    io_bench,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = io_runtime_context
    load_config(
        io_bench(
            """
            [[io.dio]]
            dio_id = 1
            driver = ftdi-ft232h
            resource = ftdi://ftdi:232h/1
            port_lines = 8
            direction = 0xFF
            """,
        )
    )
    import colosseum_equipment.io.backends.ftdi.dio as ftdi_mod

    monkeypatch.setattr(ftdi_mod, "_gpio_controller", None)
    assert col.io.dio.write_port(dio_id=1, value=0) is None
    row = ctx.db.fetch_table_rows("commands")[-1]
    assert row["status"] == "ERROR"
    assert "colosseum[io]" in (row["message"] or "")


def test_io_i2c_stub_records_command_error(io_runtime_context: RuntimeContext, io_bench) -> None:
    ctx = io_runtime_context
    load_config(
        io_bench(
            """
            [[io.i2c]]
            bus_id = 1
            driver = ni-845x
            """,
        )
    )
    assert col.io.i2c.write(bus_id=1, address=0x50, data=b"\x00") is None
    row = ctx.db.fetch_table_rows("commands")[-1]
    assert row["status"] == "ERROR"
    assert "ni-845x" in (row["message"] or "")


def test_io_spi_stub_records_command_error(io_runtime_context: RuntimeContext, io_bench) -> None:
    ctx = io_runtime_context
    load_config(
        io_bench(
            """
            [[io.spi]]
            bus_id = 1
            """,
        )
    )
    assert col.io.spi.write(bus_id=1, data=b"\x01") is None
    row = ctx.db.fetch_table_rows("commands")[-1]
    assert row["status"] == "ERROR"
    assert "NI USB-845x" in (row["message"] or "")
