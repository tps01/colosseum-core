"""No-artifacts utility mode: console-only logging and in-memory SQLite."""

from __future__ import annotations

import pytest

import colosseum as col
import colosseum.context as context_module
from colosseum.config.loader import load_config
from colosseum.context import apply_no_artifacts, init_context, require_context
from colosseum.output.artifacts import resolve_artifact_path
from colosseum.output.paths import ensure_output_dir, ensure_runtime_ready

from tests.support.helpers import run_endex_expect_code


@pytest.fixture(autouse=True)
def _reset_context() -> None:
    context_module._ACTIVE_CONTEXT = None
    yield
    context_module._ACTIVE_CONTEXT = None


def test_load_config_no_artifacts_skips_outputs(bench_sim, isolated_cwd, capsys) -> None:
    load_config(bench_sim, no_artifacts=True)
    col.equipment.psu.set_voltage(psu_id=1, voltage=3.3)

    assert not (isolated_cwd / "outputs").exists()
    captured = capsys.readouterr()
    assert "Colosseum version:" in captured.out
    assert "no-artifacts mode" in captured.out

    measurements = col.database.read_measurements()
    assert measurements == []


def test_ensure_output_dir_raises_in_no_artifacts_mode(bench_sim) -> None:
    load_config(bench_sim, no_artifacts=True)
    ctx = require_context()
    ensure_runtime_ready(ctx)

    with pytest.raises(RuntimeError, match="no-artifacts mode"):
        ensure_output_dir(ctx)


def test_resolve_artifact_path_raises_in_no_artifacts_mode(bench_sim) -> None:
    load_config(bench_sim, no_artifacts=True)
    col.equipment.psu.set_voltage(psu_id=1, voltage=3.3)

    with pytest.raises(RuntimeError, match="no-artifacts mode"):
        resolve_artifact_path("traces/foo.csv")


def test_late_no_artifacts_toggle_raises(bench_sim) -> None:
    load_config(bench_sim)
    ctx = require_context()
    ensure_runtime_ready(ctx)

    with pytest.raises(RuntimeError, match="before the runtime is bootstrapped"):
        apply_no_artifacts(ctx, no_artifacts=True)


def test_endex_no_artifacts_skips_summary(bench_sim, isolated_cwd) -> None:
    load_config(bench_sim, no_artifacts=True)
    col.equipment.psu.set_voltage(psu_id=1, voltage=3.3)

    run_endex_expect_code(0)

    assert not (isolated_cwd / "outputs").exists()


def test_init_context_honors_env_no_artifacts(bench_sim, isolated_cwd, monkeypatch) -> None:
    monkeypatch.setenv("COLOSSEUM_NO_ARTIFACTS", "1")
    init_context(test_case_name="env_flag")
    load_config(bench_sim)
    col.equipment.psu.set_voltage(psu_id=1, voltage=3.3)

    assert require_context().no_artifacts is True
    assert not (isolated_cwd / "outputs").exists()
