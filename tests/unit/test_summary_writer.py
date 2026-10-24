"""Summary artifact content."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from colosseum.decorators.verification import VerificationResult
from colosseum.runner.runtime import SuiteSlotResult
from colosseum.summary.writer import SuiteSummaryWriter, SummaryWriter


def test_summary_lists_failed_required(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    out = ctx.output_dir
    assert out is not None
    ctx.result_aggregator.record_verification(
        VerificationResult(status="FAIL", message="out of tolerance", optional=False),
        key="rail_a",
        command="verify_voltage",
        domain="equipment",
    )
    SummaryWriter().write(out, ctx.result_aggregator, ctx)
    text = (out / "summary.txt").read_text(encoding="utf-8")
    assert "Overall result: FAIL" in text
    assert "rail_a" in text
    assert "Exit code: 1" in text
    import json

    payload = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert payload["overall_result"] == "FAIL"
    assert payload["exit_code"] == 1
    assert payload["failed_required_verifications"][0]["key"] == "rail_a"


def test_summary_prints_verification_description(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    out = ctx.output_dir
    assert out is not None
    ctx.result_aggregator.record_verification(
        VerificationResult(status="FAIL", message="out of tolerance", optional=False),
        key="rail_a",
        command="verify_voltage",
        domain="equipment",
        description="Verify rail voltage",
    )
    ctx.result_aggregator.record_verification(
        VerificationResult(status="FAIL", message="other", optional=False),
        key="rail_b",
        command="verify_voltage",
        domain="equipment",
    )
    SummaryWriter().write(out, ctx.result_aggregator, ctx)
    text = (out / "summary.txt").read_text(encoding="utf-8")
    assert (
        "[verification] Verify rail voltage equipment.verify_voltage key=rail_a: "
        "out of tolerance"
    ) in text
    assert "[verification] equipment.verify_voltage key=rail_b: other" in text
    payload = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    described, plain = payload["failed_required_verifications"]
    assert described["description"] == "Verify rail voltage"
    assert plain["description"] == ""


def test_summary_json_splits_failed_commands_from_verifications(unit_runtime_context) -> None:
    import json

    from colosseum.decorators import CommandResult

    ctx = unit_runtime_context
    out = ctx.output_dir
    assert out is not None
    ctx.result_aggregator.record_verification(
        VerificationResult(status="FAIL", message="rail low", optional=False),
        key="rail_a",
        command="verify_voltage",
        domain="equipment",
    )
    ctx.result_aggregator.record_command(
        CommandResult(status="ERROR", message="set failed", optional=False),
        key="rail_a",
        command="set_voltage",
        domain="equipment",
    )
    ctx.result_aggregator.record_verification(
        VerificationResult(status="FAIL", message="noise", optional=True),
        key="probe",
        command="verify_noise",
        domain="equipment",
    )
    SummaryWriter().write(out, ctx.result_aggregator, ctx)
    payload = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert payload["overall_result"] == "FAIL"
    assert payload["exit_code"] == 1
    kinds = {row["kind"] for row in payload["failed_required_outcomes"]}
    assert kinds == {"verification", "command"}
    assert [row["key"] for row in payload["failed_required_verifications"]] == ["rail_a"]
    text = (out / "summary.txt").read_text(encoding="utf-8")
    assert "[verification]" in text
    assert "[command]" in text
    assert "Optional outcomes:" in text


def _slot(
    directory: Path,
    script_name: str,
    *,
    test_index: int,
    overall: str,
    repeat_index: int | None = None,
) -> SuiteSlotResult:
    return SuiteSlotResult(
        phase="test",
        script_path=Path(script_name),
        output_dir=directory,
        test_index=test_index,
        repeat_index=repeat_index,
        affects_suite_result=True,
        overall=overall,
        exit_code=0 if overall == "PASS" else 1,
    )


def _write_failures(directory: Path, rows: list[dict[str, str]]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    payload = {"failed_required_verifications": rows}
    (directory / "summary.json").write_text(json.dumps(payload), encoding="utf-8")


def test_suite_summary_reports_slot_rates_and_runtime(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    root = ctx.output_dir
    assert root is not None
    container = root / "container"
    container.mkdir()
    started = datetime(2026, 10, 23, 18, 0, tzinfo=timezone.utc)
    ctx.suite_started_at = started
    ctx.suite_name = "boot_soak"
    slots = []
    for index, overall in enumerate(("PASS", "PASS", "PASS", "FAIL")):
        slot_dir = root / f"slot-{index}"
        slot_dir.mkdir()
        slots.append(_slot(slot_dir, "case.py", test_index=index, overall=overall))
    ctx.suite_test_results = slots

    SuiteSummaryWriter().write(container, ctx, exit_code=1, overall="FAIL")

    text = (container / "summary.txt").read_text(encoding="utf-8")
    payload = json.loads((container / "summary.json").read_text(encoding="utf-8"))
    ended = datetime.fromisoformat(payload["end_time_utc"])
    assert "Test slots: 4 (3 pass, 1 fail)" in text
    assert "Pass: 75.0%" in text
    assert "Fail: 25.0%" in text
    assert "Start time: 2026-10-23T18:00:00+00:00" in text
    assert f"Runtime: {ended - started}" in text
    assert "Most common failed verifications:" not in text
    assert payload["test_slot_counts"] == {
        "total": 4,
        "pass": 3,
        "fail": 1,
        "pass_percent": 75.0,
        "fail_percent": 25.0,
    }
    assert payload["start_time_utc"] == "2026-10-23T18:00:00+00:00"
    assert payload["duration_seconds"] == (ended - started).total_seconds()


def test_suite_summary_ranks_repeated_verification_failures(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    root = ctx.output_dir
    assert root is not None
    container = root / "container"
    container.mkdir()
    boot_a = root / "boot-0"
    boot_b = root / "boot-1"
    boot_b.mkdir()
    _write_failures(
        boot_a,
        [
            {
                "domain": "equipment",
                "command": "verify_voltage",
                "key": f"v{index:02d}",
                "message": "low",
            }
            for index in range(11)
        ],
    )
    rail_a = root / "rail-0"
    rail_b = root / "rail-1"
    _write_failures(
        rail_a,
        [
            {
                "domain": "equipment",
                "command": "verify_voltage",
                "key": "rail_a",
                "message": "low",
            },
            {
                "domain": "equipment",
                "command": "verify_voltage",
                "key": "rail_a",
                "message": "lower",
            },
        ],
    )
    _write_failures(
        rail_b,
        [
            {
                "domain": "equipment",
                "command": "verify_voltage",
                "key": "rail_a",
                "message": "other",
            },
        ],
    )
    solo = root / "solo"
    _write_failures(
        solo,
        [
            {
                "domain": "equipment",
                "command": "verify_voltage",
                "key": "solo",
                "message": "once",
            },
        ],
    )
    ctx.suite_test_results = [
        _slot(boot_a, "boot_verify.py", test_index=0, overall="FAIL", repeat_index=0),
        _slot(boot_b, "boot_verify.py", test_index=0, overall="FAIL", repeat_index=1),
        _slot(solo, "only_once.py", test_index=1, overall="FAIL"),
        _slot(rail_a, "rail.py", test_index=2, overall="FAIL", repeat_index=0),
        _slot(rail_b, "rail.py", test_index=2, overall="FAIL", repeat_index=1),
    ]

    SuiteSummaryWriter().write(container, ctx, exit_code=1, overall="FAIL")

    text = (container / "summary.txt").read_text(encoding="utf-8")
    payload = json.loads((container / "summary.json").read_text(encoding="utf-8"))
    ranked = payload["common_failed_verifications"]
    assert "key=solo" not in text
    assert "key=v09" not in text
    assert "key=v10" not in text
    assert "  - 2x test=2 rail.py equipment.verify_voltage key=rail_a" in text
    assert "  - 1x test=0 boot_verify.py equipment.verify_voltage key=v08" in text
    assert [row["key"] for row in ranked] == ["rail_a", *[f"v{index:02d}" for index in range(9)]]
    assert ranked[0]["count"] == 2
    assert all(row["count"] == 1 for row in ranked[1:])


def test_suite_summary_without_test_slots_omits_rates_and_timing(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    root = ctx.output_dir
    assert root is not None
    container = root / "container"
    container.mkdir()
    ctx.suite_started_at = None
    ctx.suite_test_results = []

    SuiteSummaryWriter().write(container, ctx, exit_code=0, overall="PASS")

    text = (container / "summary.txt").read_text(encoding="utf-8")
    payload = json.loads((container / "summary.json").read_text(encoding="utf-8"))
    assert "Test slots: 0 (0 pass, 0 fail)" in text
    assert "Pass:" not in text
    assert "Start time:" not in text
    assert "Runtime:" not in text
    assert "Most common failed verifications:" not in text
    assert "start_time_utc" not in payload
    assert "duration_seconds" not in payload
    assert payload["test_slot_counts"] == {"total": 0, "pass": 0, "fail": 0}
    assert payload["common_failed_verifications"] == []
