from __future__ import annotations

from pathlib import Path

import pytest

import colosseum as col
from colosseum.config import load_config
from colosseum.context import init_context
from colosseum_equipment.connections import close_all


def _write_bench(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "bench.toml"
    path.write_text(body, encoding="utf-8")
    return path


def _init_with_bench(tmp_path: Path, body: str, *, test_case_name: str):
    bench = _write_bench(tmp_path, body)
    ctx = init_context(test_case_name=test_case_name, config_path=bench)
    load_config(bench)
    return ctx


def test_io_write_pin_without_config_records_command_error() -> None:
    ctx = init_context(test_case_name="io_no_config")
    assert col.io.dio.write_pin(dio_id=1, line=0, value=True) is None
    row = ctx.db.fetch_table_rows("commands")[-1]
    assert row["status"] == "ERROR"
    assert ctx.result_aggregator.overall_pass() is False


def test_io_write_pin_stub_driver_records_command_error(tmp_path: Path) -> None:
    ctx = _init_with_bench(
        tmp_path,
        """
[[io.dio]]
dio_id = 1
""",
        test_case_name="io_stub_driver",
    )
    assert col.io.dio.write_pin(dio_id=1, line=0, value=True) is None
    row = ctx.db.fetch_table_rows("commands")[-1]
    assert row["status"] == "ERROR"
    assert "NI 6501" in (row["message"] or "")


def test_io_dio_sim_read_write_port(tmp_path: Path) -> None:
    _init_with_bench(
        tmp_path,
        """
[[io.dio]]
dio_id = 1
driver = sim
port_lines = 8
direction = 0xFF
""",
        test_case_name="io_sim_port",
    )
    col.io.dio.write_port(dio_id=1, value=0b1010)
    assert col.io.dio.read_port(dio_id=1, key="port_a") == 0b1010
    col.io.dio.write_pin(dio_id=1, line=0, value=True)
    assert col.io.dio.read_pin(dio_id=1, line=0, key="line0") is True


def test_io_dio_sim_measurement_domain_equipment(tmp_path: Path) -> None:
    ctx = _init_with_bench(
        tmp_path,
        """
[[io.dio]]
dio_id = 1
driver = sim
port_lines = 8
direction = 0xFF
""",
        test_case_name="io_sim_domain",
    )
    col.io.dio.write_port(dio_id=1, value=3)
    col.io.dio.read_port(dio_id=1, key="p1")
    rows = ctx.db.list_measurements(domain="equipment", command="io.dio.read_port", key="p1")
    assert len(rows) == 1
    assert rows[0].value == 3


def test_io_connections_close_all(tmp_path: Path) -> None:
    ctx = _init_with_bench(
        tmp_path,
        """
[[io.dio]]
dio_id = 1
driver = sim
port_lines = 8
direction = 0xFF
""",
        test_case_name="io_close_all",
    )
    col.io.dio.write_port(dio_id=1, value=1)
    assert "io:backend:dio:1" in ctx.resource_cache
    close_all()
    assert "io:backend:dio:1" not in ctx.resource_cache


def test_io_ftdi_missing_extra_records_command_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = _init_with_bench(
        tmp_path,
        """
[[io.dio]]
dio_id = 1
driver = ftdi-ft232h
resource = ftdi://ftdi:232h/1
port_lines = 8
direction = 0xFF
""",
        test_case_name="io_ftdi_missing",
    )
    import colosseum_equipment.io.backends.ftdi.dio as ftdi_mod

    monkeypatch.setattr(ftdi_mod, "_gpio_controller", None)
    assert col.io.dio.write_port(dio_id=1, value=0) is None
    row = ctx.db.fetch_table_rows("commands")[-1]
    assert row["status"] == "ERROR"
    assert "colosseum[io]" in (row["message"] or "")


def test_io_i2c_stub_records_command_error(tmp_path: Path) -> None:
    ctx = _init_with_bench(
        tmp_path,
        """
[[io.i2c]]
bus_id = 1
driver = ni-845x
""",
        test_case_name="io_i2c_stub",
    )
    assert col.io.i2c.write(bus_id=1, address=0x50, data=b"\x00") is None
    row = ctx.db.fetch_table_rows("commands")[-1]
    assert row["status"] == "ERROR"
    assert "ni-845x" in (row["message"] or "")


def test_io_spi_stub_records_command_error(tmp_path: Path) -> None:
    ctx = _init_with_bench(
        tmp_path,
        """
[[io.spi]]
bus_id = 1
""",
        test_case_name="io_spi_stub",
    )
    assert col.io.spi.write(bus_id=1, data=b"\x01") is None
    row = ctx.db.fetch_table_rows("commands")[-1]
    assert row["status"] == "ERROR"
    assert "NI USB-845x" in (row["message"] or "")
