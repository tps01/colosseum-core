"""BLOCKED owed keys and opt-in report listeners at finalize."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from colosseum.config.parameters import attach_parameters
from colosseum.decorators import command
from colosseum.exceptions import ProceduralFault
from colosseum.plugins.registry import register_builtin_listeners
from colosseum.database import CommandRecord, VerificationRecord
from colosseum.results.finalize import FinalizeRunResult, finalize_run
from colosseum.results.finalize_policy import FinalizePolicy
from colosseum.summary.junit import write_junit_report


def _policy() -> FinalizePolicy:
    return FinalizePolicy(
        kind="single",
        write_summary=True,
        rename_dir=False,
        scores_suite=True,
        run_shutdown=False,
        close_resources=True,
        log_overall=False,
    )


@pytest.fixture
def ctx(unit_runtime_context, tmp_path: Path):
    unit_runtime_context.output_dir = tmp_path
    unit_runtime_context.test_case_name = "blocked_demo"
    unit_runtime_context.runtime_ready = True
    register_builtin_listeners(unit_runtime_context.plugin_registry)
    return unit_runtime_context


def _attach_limits(ctx, tmp_path: Path) -> Path:
    path = tmp_path / "parameters.toml"
    path.write_text(
        "[rail]\nexpected_val = 3.3\ntolerance = 0.1\n",
        encoding="utf-8",
    )
    attach_parameters(ctx, path)
    return path


def test_owed_key_blocked_after_unit_command_error(ctx, tmp_path: Path) -> None:
    _attach_limits(ctx, tmp_path)

    @command
    def power_on() -> None:
        raise RuntimeError("DUT silent")

    with pytest.raises(RuntimeError):
        power_on()

    result = finalize_run(ctx, policy=_policy())
    assert result.exit_code == 1
    blocked = [row for row in result.verifications if row.key == "rail"]
    assert len(blocked) == 1
    assert blocked[0].status == "BLOCKED"
    assert blocked[0].actual is None
    assert "power_on" in blocked[0].message


def test_blocked_is_wats_f_when_enabled(ctx, tmp_path: Path) -> None:
    _attach_limits(ctx, tmp_path)
    ctx.enabled_reports = frozenset({"wats"})

    @command
    def power_on() -> None:
        raise RuntimeError("DUT silent")

    with pytest.raises(RuntimeError):
        power_on()

    result = finalize_run(ctx, policy=_policy())
    assert result.exit_code == 1
    wats_files = list(tmp_path.glob("wats_*.json"))
    assert len(wats_files) == 1
    payload = json.loads(wats_files[0].read_text(encoding="utf-8"))
    assert payload["result"] == "F"
    step = next(s for s in payload["root"]["steps"] if s["tsGuid"] == "rail")
    assert step["status"] == "F"
    assert "reportText" in step
    assert "numericMeas" not in step


def test_procedural_fault_is_wats_e(ctx, tmp_path: Path) -> None:
    ctx.enabled_reports = frozenset({"wats"})

    @command
    def open_session(*, key: str = "") -> None:
        raise ProceduralFault("resource never opened")

    with pytest.raises(ProceduralFault):
        open_session(key="bench")

    result = finalize_run(ctx, policy=_policy())
    assert result.exit_code == 1
    wats_files = list(tmp_path.glob("wats_*.json"))
    assert len(wats_files) == 1
    payload = json.loads(wats_files[0].read_text(encoding="utf-8"))
    assert payload["result"] == "E"


def test_no_report_writes_summary_not_wats_or_junit(ctx, tmp_path: Path) -> None:
    ctx.enabled_reports = frozenset()
    from colosseum.logging.setup import setup_logging

    setup_logging(ctx, console=False, file=True)
    result = finalize_run(ctx, policy=_policy())
    assert result.exit_code == 0
    assert (tmp_path / "summary.txt").is_file()
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "debug.log").is_file()
    assert list(tmp_path.glob("wats_*.json")) == []
    assert not (tmp_path / "junit.xml").exists()


def test_junit_blocked_failure_and_command_error(ctx, tmp_path: Path) -> None:
    result = FinalizeRunResult(
        exit_code=1,
        overall="FAIL",
        measurement_count=0,
        command_count=1,
        verifications=[
            VerificationRecord(
                domain="core",
                command="owed_limit",
                key="rail",
                status="BLOCKED",
                message="not measured",
                optional=False,
            ),
        ],
        measurements=[],
        commands=[
            CommandRecord(
                domain="core",
                command="power_on",
                key="boot",
                status="ERROR",
                optional=False,
                message="DUT silent",
                cause="unit",
            ),
        ],
    )
    path = write_junit_report(tmp_path, ctx, result)
    root = ET.parse(path).getroot()
    cases = root.findall("testcase")
    assert len(cases) == 1
    failure = cases[0].find("failure")
    assert failure is not None
    assert failure.get("type") == "BLOCKED"

    empty = FinalizeRunResult(
        exit_code=1,
        overall="FAIL",
        measurement_count=0,
        command_count=1,
        verifications=[],
        measurements=[],
        commands=[
            CommandRecord(
                domain="core",
                command="power_on",
                key="",
                status="ERROR",
                optional=False,
                message="aborted",
                cause="unit",
            ),
        ],
    )
    path2 = write_junit_report(tmp_path, ctx, empty)
    root2 = ET.parse(path2).getroot()
    cases2 = root2.findall("testcase")
    assert len(cases2) == 1
    assert cases2[0].find("error") is not None


def test_raising_listener_leaves_exit_and_other_listener(ctx, tmp_path: Path) -> None:
    def boom(_output_dir, _result, _ctx) -> None:
        raise RuntimeError("listener boom")

    registry = ctx.plugin_registry
    if "boom" not in registry.listener_names():
        registry.register_listener("boom", boom)
    ctx.enabled_reports = frozenset({"boom", "junit"})

    @command
    def ok(*, key: str = "") -> str:
        return "ok"

    ok(key="step")
    result = finalize_run(ctx, policy=_policy())
    assert result.exit_code == 0
    assert (tmp_path / "junit.xml").is_file()
    assert (tmp_path / "summary.json").is_file()


def test_missing_measurement_blocked_after_unit_error(ctx) -> None:
    from colosseum.decorators.verification import missing_measurement_result

    @command
    def power_on(*, key: str = "") -> None:
        raise RuntimeError("dark")

    with pytest.raises(RuntimeError):
        power_on()
    result = missing_measurement_result(key="rail")
    assert result.status == "BLOCKED"
