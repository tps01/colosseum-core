from __future__ import annotations

import json
from pathlib import Path

from colosseum.gui._browser import (
    display_status,
    format_summary_text,
    load_run_browser_snapshot,
    load_run_snapshot,
)
from colosseum.gui.app import _STATUS_BUTTON_COLORS, _normalize_status


def test_load_run_browser_snapshot_reads_statuses(isolated_cwd) -> None:
    pass_run = isolated_cwd / "outputs" / "2026-01-01_120000_pass-pass"
    incomplete_run = isolated_cwd / "playground" / "outputs" / "2026-01-01_120001_incomplete"
    pass_run.mkdir(parents=True)
    incomplete_run.mkdir(parents=True)
    (pass_run / "summary.json").write_text('{"overall_result": "PASS"}', encoding="utf-8")

    snapshot = load_run_browser_snapshot(isolated_cwd)

    statuses = {row.entry.path.name: row.status for row in snapshot.rows}
    assert statuses[pass_run.name] == "PASS"
    assert statuses[incomplete_run.name] == "incomplete"
    assert snapshot.output_dirs == {pass_run.parent, incomplete_run.parent}
    assert all(row.children == () for row in snapshot.rows)


def test_load_run_browser_snapshot_nests_suite_cases(isolated_cwd: Path) -> None:
    suite = isolated_cwd / "outputs" / "2026-01-01_120000_rail-fail"
    first = suite / "2026-01-01_120000_pass_case-pass"
    second = suite / "2026-01-01_120001_fail_case-fail"
    extra = suite / "2026-01-01_120002_extra-pass"
    loose = suite / "notes"
    for path in (first, second, extra, loose):
        path.mkdir(parents=True)
    (loose / "note.txt").write_text("x", encoding="utf-8")
    (suite / "summary.json").write_text(
        json.dumps(
            {
                "overall_result": "FAIL",
                "all_slots": [
                    {"output_directory": str(isolated_cwd / "missing" / first.name)},
                    {"output_directory": str(isolated_cwd / "missing" / second.name)},
                ],
            },
        ),
        encoding="utf-8",
    )
    (first / "summary.json").write_text('{"overall_result": "PASS"}', encoding="utf-8")
    (second / "summary.json").write_text('{"overall_result": "FAIL"}', encoding="utf-8")
    (extra / "summary.json").write_text('{"overall_result": "PASS"}', encoding="utf-8")

    snapshot = load_run_browser_snapshot(isolated_cwd)

    assert [row.entry.path for row in snapshot.rows] == [suite]
    row = snapshot.rows[0]
    assert row.status == "FAIL"
    names = [child.entry.path.name for child in row.children]
    assert names == [first.name, second.name, extra.name]
    assert [child.status for child in row.children] == ["PASS", "FAIL", "PASS"]


def test_load_run_snapshot_reads_debug_log(isolated_cwd) -> None:
    run_dir = isolated_cwd / "outputs" / "2026-01-01_120000_pass-pass"
    run_dir.mkdir(parents=True)
    (run_dir / "debug.log").write_text("hello\nworld\n", encoding="utf-8")
    (run_dir / "summary.json").write_text('{"overall_result": "PASS", "exit_code": 0}', encoding="utf-8")

    snapshot = load_run_snapshot(run_dir)

    assert snapshot.log_error is None
    assert snapshot.log_text == "hello\nworld\n"
    assert snapshot.summary is not None
    assert snapshot.summary["overall_result"] == "PASS"


def test_load_run_snapshot_preserves_slot_identity_header(isolated_cwd) -> None:
    """GUI log pane source returns slot debug.log text, including the identity header."""
    run_dir = isolated_cwd / "outputs" / "2026-01-01_120000_pass_test-pass"
    run_dir.mkdir(parents=True)
    header = (
        "2026-01-01 12:00:00,000 INFO [colosseum] Colosseum version: 0.16.2\n"
        "2026-01-01 12:00:00,000 INFO [colosseum] Python version: 3.12.4\n"
        "2026-01-01 12:00:00,000 INFO [colosseum] Platform: Windows-11\n"
        "2026-01-01 12:00:00,000 INFO [colosseum] Test case: pass_test\n"
        "2026-01-01 12:00:00,000 INFO [colosseum] Suite: fixture_happy\n"
        "2026-01-01 12:00:00,000 INFO [colosseum] Start time: 2026-01-01T17:00:00+00:00\n"
        "2026-01-01 12:00:00,000 INFO [colosseum] Config file: C:\\tmp\\config.toml\n"
        f"2026-01-01 12:00:00,000 INFO [colosseum] Output directory: {run_dir}\n"
        "2026-01-01 12:00:00,100 INFO [colosseum] Running script pass_test.py (phase=test)\n"
    )
    (run_dir / "debug.log").write_text(header, encoding="utf-8")
    (run_dir / "summary.json").write_text('{"overall_result": "PASS", "exit_code": 0}', encoding="utf-8")

    snapshot = load_run_snapshot(run_dir)

    assert snapshot.log_error is None
    assert snapshot.log_text == header
    assert snapshot.log_text.count("Colosseum version:") == 1
    assert "Test case: pass_test" in snapshot.log_text
    assert f"Output directory: {run_dir}" in snapshot.log_text


def test_load_run_snapshot_missing_log(isolated_cwd) -> None:
    run_dir = isolated_cwd / "outputs" / "2026-01-01_120000_pass-pass"
    run_dir.mkdir(parents=True)

    snapshot = load_run_snapshot(run_dir)

    assert snapshot.log_text is None
    assert snapshot.log_error is not None
    assert "No debug.log" in snapshot.log_error


def test_format_summary_text_includes_failed_verifications() -> None:
    text = format_summary_text(
        {
            "overall_result": "FAIL",
            "exit_code": 1,
            "verification_counts": {"required": {"FAIL": 1}, "optional": {}},
            "failed_required_verifications": [
                {
                    "status": "FAIL",
                    "domain": "core",
                    "command": "verify",
                    "key": "voltage",
                    "message": "out of range",
                },
            ],
        },
    )

    assert "Overall: FAIL" in text
    assert "Failed required verifications:" in text
    assert "core.verify key=voltage" in text
    assert "Verifications (required): 1 (FAIL 1)" in text


def test_display_status_marks_crashes_and_incomplete_runs() -> None:
    assert display_status(None) == "incomplete"
    assert display_status({"overall_result": "FAIL"}) == "FAIL"
    crashed = {"overall_result": "FAIL", "suite_error": "test script failed"}
    assert display_status(crashed) == "ERROR"
    suite_crash = {
        "overall_result": "FAIL",
        "suite_fail_reason": "test_failure:a.py:script_error",
    }
    assert display_status(suite_crash) == "ERROR"
    assert display_status({}) == "incomplete"


def test_format_summary_text_includes_command_and_slot_context() -> None:
    text = format_summary_text(
        {
            "overall_result": "FAIL",
            "exit_code": 1,
            "suite_error": "test script failed",
            "command_counts": {"required": {"ERROR": 1}, "optional": {}},
            "failed_required_outcomes": [
                {
                    "kind": "command",
                    "domain": "core",
                    "command": "arm",
                    "key": "dev",
                    "status": "ERROR",
                    "message": "boom",
                },
            ],
            "all_slots": [
                {
                    "phase": "test",
                    "overall_result": "FAIL",
                    "script": "pass_rail.py",
                    "repeat_index": 1,
                    "cycle_index": 2,
                },
            ],
        },
    )
    assert "Suite error: test script failed" in text
    assert "Commands (required outcomes): 1 (ERROR 1)" in text
    assert "Failed required commands:" in text
    assert "test [FAIL] repeat=1 cycle=2 pass_rail.py" in text


def test_format_summary_text_includes_suite_slot_metrics() -> None:
    text = format_summary_text(
        {
            "overall_result": "FAIL",
            "exit_code": 1,
            "end_time_utc": "2026-10-23T18:00:10+00:00",
            "start_time_utc": "2026-10-23T18:00:00+00:00",
            "duration_seconds": 10,
            "test_slot_counts": {
                "total": 4,
                "pass": 3,
                "fail": 1,
                "pass_percent": 75.0,
                "fail_percent": 25.0,
            },
            "common_failed_verifications": [
                {
                    "count": 2,
                    "test_index": 0,
                    "script": "boot_verify.py",
                    "domain": "equipment",
                    "command": "verify_voltage",
                    "key": "rail_a",
                },
            ],
        },
    )
    assert "Test slots: 4 (3 pass, 1 fail)" in text
    assert "Pass: 75.0%" in text
    assert "Fail: 25.0%" in text
    assert "Start time: 2026-10-23T18:00:00+00:00" in text
    assert "Runtime: 0:00:10" in text
    assert "2x test=0 boot_verify.py equipment.verify_voltage key=rail_a" in text


def test_error_and_incomplete_use_purple() -> None:
    purple = _STATUS_BUTTON_COLORS["NO TEST"]
    assert _STATUS_BUTTON_COLORS[_normalize_status("ERROR")] == purple
    assert _STATUS_BUTTON_COLORS[_normalize_status("incomplete")] == purple
    assert _STATUS_BUTTON_COLORS[_normalize_status("FAIL")] != purple
