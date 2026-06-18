"""Host plugin measurement and verification APIs."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from colosseum_host.api import bench, config, system
from colosseum_host.api._verify import verify_minimum


@pytest.fixture
def ctx(unit_runtime_context):
    return unit_runtime_context


def test_measure_python_version_records_host_domain(ctx) -> None:
    system.measure_python_version(key="py")
    row = ctx.db.get_measurement("host", "system.measure_python_version", "py", row_index=0)
    assert row is not None
    assert row.value


def test_verify_memory_minimum_pass_and_fail(ctx) -> None:
    system.measure_memory_available_mb(key="mem")
    pass_result = verify_minimum(
        domain="host",
        command="system.measure_memory_available_mb",
        key="mem",
        minimum=0.0,
    )
    assert pass_result.status == "PASS"
    fail_result = verify_minimum(
        domain="host",
        command="system.measure_memory_available_mb",
        key="mem",
        minimum=1e12,
    )
    assert fail_result.status == "FAIL"


def test_verify_python_version_prefix(ctx) -> None:
    system.measure_python_version(key="py")
    result = system.verify_python_version(key="py", version_prefix="3.")
    assert result.status == "PASS"


def test_verify_platform_exact(ctx) -> None:
    system.measure_platform(key="plat")
    row = ctx.db.get_measurement("host", "system.measure_platform", "plat", row_index=0)
    result = system.verify_platform(key="plat", expected_platform=str(row.value))
    assert result.status == "PASS"


def test_measure_visa_backend(ctx) -> None:
    mock_rm = MagicMock()
    mock_rm.return_value.visalib = "@sim"
    with patch("pyvisa.ResourceManager", mock_rm):
        bench.measure_visa_backend(key="visa")
    row = ctx.db.get_measurement("host", "bench.measure_visa_backend", "visa", row_index=0)
    assert row is not None
    assert "@sim" in str(row.value)


def test_verify_visa_available_allows_sim_by_default(ctx) -> None:
    mock_rm = MagicMock()
    mock_rm.return_value.visalib = "@sim"
    with patch("pyvisa.ResourceManager", mock_rm):
        bench.measure_visa_backend(key="visa")
    result = bench.verify_visa_available(key="visa")
    assert result.status == "PASS"


def test_capture_host_profile_writes_artifact(ctx) -> None:
    written = config.capture_host_profile(path="host_profile.json")
    path = Path(written)
    assert path.is_file()
    assert path.read_text(encoding="utf-8").strip().startswith("{")


def test_verify_bench_config_loaded_without_config(ctx) -> None:
    result = config.verify_bench_config_loaded(key="cfg")
    assert result.status == "FAIL"


def test_verify_bench_config_loaded_with_config(ctx, tmp_path) -> None:
    ctx.config_path = tmp_path / "bench.toml"
    result = config.verify_bench_config_loaded(key="cfg")
    assert result.status == "PASS"
