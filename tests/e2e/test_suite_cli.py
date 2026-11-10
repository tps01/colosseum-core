"""E2E-SUITE: colosseum run-suite via subprocess."""

from __future__ import annotations

import json

import pytest

from tests.support.e2e_specifications import (
    assert_provenance_artifact,
    assert_suite_container,
    assert_supporting_slot_artifacts,
    assert_test_slot_full_artifacts,
    assert_wats_identity_fields,
    load_wats_json,
    read_summary_json,
    run_suite_cli,
)
from tests.support.helpers import latest_suite_container, query_db, slot_dirs_matching, REPO_ROOT as REPO

METADATA = REPO / "tests" / "fixtures" / "metadata_example.yaml"


def _suite(fixtures_dir, name: str):
    return fixtures_dir / "suites" / name


def _slot(container, stem: str):
    matches = slot_dirs_matching(container, stem)
    assert matches, f"no slot matching {stem!r}"
    return matches[-1]


def _assert_slot_has_no_provenance(slot_dir) -> None:
    log_text = (slot_dir / "debug.log").read_text(encoding="utf-8")
    assert "Provenance:" not in log_text
    assert query_db(slot_dir, "SELECT COUNT(*) FROM provenance") == [(0,)]
    summary_path = slot_dir / "summary.json"
    if summary_path.is_file():
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        assert "provenance" not in payload


def test_missing_suite_file_prints_stderr(core_config, isolated_cwd, subprocess_env) -> None:
    """Missing suite path exits 1 with a clear stderr message."""
    proc = run_suite_cli(
        isolated_cwd / "no_such_suite.toml",
        core_config,
        isolated_cwd,
        subprocess_env,
    )
    assert proc.returncode == 1
    assert "Suite file not found:" in proc.stderr


def test_missing_suite_config_prints_stderr(fixtures_dir, isolated_cwd, subprocess_env) -> None:
    """Missing -g config for run-suite exits 1 with a clear stderr message."""
    proc = run_suite_cli(
        _suite(fixtures_dir, "happy.toml"),
        isolated_cwd / "no_such_config.toml",
        isolated_cwd,
        subprocess_env,
    )
    assert proc.returncode == 1
    assert "Config file not found:" in proc.stderr


@pytest.mark.requirement("E2E-SUITE-01")
@pytest.mark.requirement("E2E-SUITE-02")
def test_happy_suite_container_passes(core_config, fixtures_dir, isolated_cwd, subprocess_env) -> None:
    """Happy suite runs setup, test, and teardown slots; container passes."""
    proc = run_suite_cli(_suite(fixtures_dir, "happy.toml"), core_config, isolated_cwd, subprocess_env)
    assert proc.returncode == 0, proc.stderr
    container = latest_suite_container(isolated_cwd)
    assert_suite_container(container, expect_pass=True)
    assert "Overall result: PASS" in (container / "summary.txt").read_text(encoding="utf-8")
    assert "Provenance:" not in proc.stdout
    assert_provenance_artifact(container)
    test_slot = _slot(container, "pass_test")
    assert (test_slot / "execution.sqlite").is_file()
    for stem in ("setup_ok", "pass_test", "teardown_ok"):
        _assert_slot_has_no_provenance(_slot(container, stem))
    assert_test_slot_full_artifacts(test_slot)
    assert_supporting_slot_artifacts(_slot(container, "setup_ok"))
    assert_supporting_slot_artifacts(_slot(container, "teardown_ok"))
    summary = read_summary_json(container)
    assert summary["overall_result"] == "PASS"
    assert len(summary["test_slots"]) == 1
    summary_text = (container / "summary.txt").read_text(encoding="utf-8")
    assert "Start time:" in summary_text
    assert "Runtime:" in summary_text
    assert "Test slots: 1 (1 pass, 0 fail)" in summary_text
    phases = {
        row[0]
        for row in query_db(
            test_slot,
            "SELECT message FROM events WHERE message LIKE 'phase_enter:%'",
        )
    }
    assert "phase_enter:test" in phases
    slots = ("setup_ok", "pass_test", "teardown_ok")
    out = proc.stdout
    assert out.count("Colosseum version:") == 1 + len(slots)
    assert out.count("Suite overall result:") == 1
    assert "Output directory: (none — no-artifacts mode)" not in out
    assert out.count("Running script ") == len(slots)
    for stem in slots:
        assert out.count(f"Test case: {stem}") == 1
        slot_dir = _slot(container, stem)
        log_text = (slot_dir / "debug.log").read_text(encoding="utf-8")
        assert log_text.count("Colosseum version:") == 1, stem
        assert f"Test case: {stem}" in log_text
        out_lines = [ln for ln in log_text.splitlines() if "Output directory:" in ln]
        assert len(out_lines) == 1, stem
        assert "no-artifacts mode" not in out_lines[0]
        assert stem in out_lines[0]
        suite_stem = container.name.removesuffix("-pass").removesuffix("-fail")
        assert suite_stem in out_lines[0]
        assert str(isolated_cwd / "outputs") in out_lines[0]


@pytest.mark.requirement("E2E-SUITE-03")
def test_setup_fail_fails_suite_without_fail_fast(core_config, fixtures_dir, isolated_cwd, subprocess_env) -> None:
    """Setup failure fails the suite even when fail_fast is false; tests still run."""
    proc = run_suite_cli(_suite(fixtures_dir, "setup_fail.toml"), core_config, isolated_cwd, subprocess_env)
    assert proc.returncode == 1, proc.stderr
    container = latest_suite_container(isolated_cwd)
    assert_suite_container(container, expect_pass=False)
    assert _slot(container, "setup_fail")
    assert _slot(container, "pass_test").name.endswith("-pass")
    assert _slot(container, "teardown_ok")
    summary = read_summary_json(container)
    assert summary["overall_result"] == "FAIL"
    assert summary["suite_failed"] is True
    assert summary["fail_fast_stopped"] is False


@pytest.mark.requirement("E2E-SUITE-04")
def test_teardown_fail_fails_suite_when_tests_pass(core_config, fixtures_dir, isolated_cwd, subprocess_env) -> None:
    """Teardown failure fails the suite even when tests pass."""
    proc = run_suite_cli(_suite(fixtures_dir, "teardown_fail.toml"), core_config, isolated_cwd, subprocess_env)
    assert proc.returncode == 1, proc.stderr
    container = latest_suite_container(isolated_cwd)
    assert_suite_container(container, expect_pass=False)
    assert _slot(container, "teardown_fail")
    summary = read_summary_json(container)
    assert summary["overall_result"] == "FAIL"
    assert summary["suite_failed"] is True


@pytest.mark.requirement("E2E-SUITE-05")
def test_test_script_crash_fails_suite(core_config, fixtures_dir, isolated_cwd, subprocess_env) -> None:
    """Test script crash fails the suite."""
    proc = run_suite_cli(_suite(fixtures_dir, "test_script_crash.toml"), core_config, isolated_cwd, subprocess_env)
    assert proc.returncode == 1, proc.stderr
    container = latest_suite_container(isolated_cwd)
    assert_suite_container(container, expect_pass=False)
    test_slot = _slot(container, "crash_test")
    errors = query_db(test_slot, "SELECT message FROM events WHERE message LIKE 'script_fail:%'")
    assert errors
    assert "Overall result: FAIL" in (container / "summary.txt").read_text(encoding="utf-8")


@pytest.mark.requirement("E2E-SUITE-06")
def test_fail_fast_stops_remaining_tests(core_config, fixtures_dir, isolated_cwd, subprocess_env) -> None:
    """fail_fast=true skips remaining tests after a test-slot failure."""
    proc = run_suite_cli(
        _suite(fixtures_dir, "multi_test_fail_fast_crash.toml"),
        core_config,
        isolated_cwd,
        subprocess_env,
    )
    assert proc.returncode == 1, proc.stderr
    container = latest_suite_container(isolated_cwd)
    assert slot_dirs_matching(container, "crash_test")
    assert slot_dirs_matching(container, "pass_test") == []
    crash_slot = _slot(container, "crash_test")
    meta = dict(query_db(crash_slot, "SELECT key, value FROM run_metadata"))
    assert meta.get("fail_fast_stopped") == "1"


@pytest.mark.requirement("E2E-SUITE-07")
def test_fail_fast_aborts_on_setup_failure(core_config, fixtures_dir, isolated_cwd, subprocess_env) -> None:
    """fail_fast=true aborts on setup failure, runs teardown, fails suite."""
    proc = run_suite_cli(_suite(fixtures_dir, "setup_fail_fail_fast.toml"), core_config, isolated_cwd, subprocess_env)
    assert proc.returncode == 1, proc.stderr
    container = latest_suite_container(isolated_cwd)
    assert_suite_container(container, expect_pass=False)
    assert _slot(container, "setup_fail")
    assert slot_dirs_matching(container, "pass_test") == []
    assert _slot(container, "teardown_ok")
    summary = read_summary_json(container)
    assert summary["suite_failed"] is True
    assert summary["fail_fast_stopped"] is True


def test_teardown_continues_after_first_failure(core_config, fixtures_dir, isolated_cwd, subprocess_env) -> None:
    """All teardown scripts run even when the first fails (fail_fast=false)."""
    proc = run_suite_cli(
        _suite(fixtures_dir, "teardown_multi_first_fail.toml"),
        core_config,
        isolated_cwd,
        subprocess_env,
    )
    assert proc.returncode == 1, proc.stderr
    container = latest_suite_container(isolated_cwd)
    assert_suite_container(container, expect_pass=False)
    assert _slot(container, "teardown_fail")
    assert _slot(container, "teardown_ok")


def test_teardown_continues_and_fails_suite_with_fail_fast(
    core_config, fixtures_dir, isolated_cwd, subprocess_env
) -> None:
    """fail_fast=true: teardown failure fails suite but later teardown scripts still run."""
    proc = run_suite_cli(
        _suite(fixtures_dir, "teardown_multi_first_fail_fast.toml"),
        core_config,
        isolated_cwd,
        subprocess_env,
    )
    assert proc.returncode == 1, proc.stderr
    container = latest_suite_container(isolated_cwd)
    assert_suite_container(container, expect_pass=False)
    assert _slot(container, "teardown_fail")
    assert _slot(container, "teardown_ok")
    summary = read_summary_json(container)
    assert summary["suite_failed"] is True


def test_fail_fast_stopped_survives_script_endex(core_config, fixtures_dir, isolated_cwd, subprocess_env) -> None:
    """fail_fast stop state is on suite summary even when the script called endex()."""
    proc = run_suite_cli(
        _suite(fixtures_dir, "fail_fast_verify_endex.toml"),
        core_config,
        isolated_cwd,
        subprocess_env,
    )
    assert proc.returncode == 1, proc.stderr
    container = latest_suite_container(isolated_cwd)
    assert slot_dirs_matching(container, "pass_test") == []
    summary = read_summary_json(container)
    assert summary["fail_fast_stopped"] is True
    assert summary["suite_failed"] is True


@pytest.mark.requirement("E2E-SUITE-08")
def test_between_tests_runs_between_executions(core_config, fixtures_dir, isolated_cwd, subprocess_env) -> None:
    """between_tests runs between test slots, not before the first or after the last."""
    proc = run_suite_cli(_suite(fixtures_dir, "between_two_tests.toml"), core_config, isolated_cwd, subprocess_env)
    assert proc.returncode == 0, proc.stderr
    container = latest_suite_container(isolated_cwd)
    sequence = (container / "sequence.txt").read_text(encoding="utf-8").splitlines()
    assert sequence == ["A", "between", "B"]
    between_slot = _slot(container, "count_between")
    phases = {
        row[0]
        for row in query_db(
            between_slot,
            "SELECT message FROM events WHERE message LIKE 'phase_enter:%'",
        )
    }
    assert "phase_enter:between_tests" in phases


@pytest.mark.requirement("E2E-SUITE-09")
def test_repeat_count_runs_between_iterations(core_config, fixtures_dir, isolated_cwd, subprocess_env) -> None:
    """repeat_count runs N iterations; between_tests runs between iterations."""
    proc = run_suite_cli(_suite(fixtures_dir, "repeat_count.toml"), core_config, isolated_cwd, subprocess_env)
    assert proc.returncode == 0, proc.stderr
    container = latest_suite_container(isolated_cwd)
    sequence = (container / "sequence.txt").read_text(encoding="utf-8").splitlines()
    assert sequence == ["test", "between", "test", "between", "test"]
    assert len(slot_dirs_matching(container, "count_repeat")) == 3
    assert len(slot_dirs_matching(container, "count_between")) == 2


@pytest.mark.requirement("E2E-SUITE-10")
def test_suite_metadata_propagates_to_wats(core_config, fixtures_dir, isolated_cwd, subprocess_env) -> None:
    """Suite --metadata propagates identity fields to test-slot WATS files."""
    proc = run_suite_cli(
        _suite(fixtures_dir, "smoke.toml"),
        core_config,
        isolated_cwd,
        subprocess_env,
        extra_args=["--metadata", str(METADATA), "--report", "wats"],
    )
    assert proc.returncode == 0, proc.stderr
    container = latest_suite_container(isolated_cwd)
    test_slot = _slot(container, "optional_fail_test")
    payload = load_wats_json(test_slot)
    assert_wats_identity_fields(
        payload,
        {
            "uut": "PARTNUMBER",
            "revision": "1.2.3",
            "serial_number": "123",
            "process_code": "1234",
            "location": "TBD_PHYSICAL_LOCATION",
            "test_intent": "Acceptance",
        },
    )


@pytest.mark.requirement("E2E-CFG-01")
def test_bad_config_exits_one(fixtures_dir, isolated_cwd, subprocess_env) -> None:
    """Invalid config TOML exits 1 before the suite runs."""
    config = isolated_cwd / "bad.toml"
    config.write_text('[runtime\nlabel = "broken"\n', encoding="utf-8")
    proc = run_suite_cli(_suite(fixtures_dir, "happy.toml"), config, isolated_cwd, subprocess_env)
    assert proc.returncode == 1
    assert not (isolated_cwd / "outputs").exists()


@pytest.mark.requirement("E2E-SUITE-11")
@pytest.mark.parametrize("flag", [["-p"], ["--mode", "procedure"]])
def test_suite_procedure_mode_skips_verifications(
    flag,
    core_config,
    fixtures_dir,
    isolated_cwd,
    subprocess_env,
) -> None:
    """Suite procedure mode runs measurements and records no verification rows."""
    proc = run_suite_cli(
        _suite(fixtures_dir, "procedure_suite.toml"),
        core_config,
        isolated_cwd,
        subprocess_env,
        extra_args=flag,
    )
    assert proc.returncode == 0, proc.stderr
    container = latest_suite_container(isolated_cwd)
    slot = _slot(container, "optional_fail_test")
    assert query_db(slot, "SELECT COUNT(*) FROM verifications")[0][0] == 0
    assert query_db(slot, "SELECT COUNT(*) FROM measurements")[0][0] >= 1


def test_suite_rejects_verify_only_mode(
    core_config,
    fixtures_dir,
    isolated_cwd,
    subprocess_env,
) -> None:
    """run-suite must reject verify_only before allocating outputs."""
    proc = run_suite_cli(
        _suite(fixtures_dir, "happy.toml"),
        core_config,
        isolated_cwd,
        subprocess_env,
        extra_args=["--mode", "verify_only"],
    )
    # argparse rejects verify_only on the suite parser (choices), or resolver errors.
    assert proc.returncode != 0
    assert not (isolated_cwd / "outputs").exists()
    combined = (proc.stderr or "") + (proc.stdout or "")
    assert "verify_only" in combined.lower() or "invalid choice" in combined.lower()


@pytest.mark.requirement("E2E-SUITE-13")
def test_suite_dry_run_passes_and_missing_key_fails(
    core_config,
    fixtures_dir,
    isolated_cwd,
    subprocess_env,
) -> None:
    """run-suite --dry-run passes a keyed script and fails a missing measurement key."""
    passed = run_suite_cli(
        _suite(fixtures_dir, "dry_run_pass.toml"),
        core_config,
        isolated_cwd,
        subprocess_env,
        extra_args=["--dry-run"],
    )
    assert passed.returncode == 0, passed.stderr + passed.stdout
    assert latest_suite_container(isolated_cwd).name.endswith("-pass")

    failed = run_suite_cli(
        _suite(fixtures_dir, "dry_run_missing_key.toml"),
        core_config,
        isolated_cwd,
        subprocess_env,
        extra_args=["--dry-run"],
    )
    assert failed.returncode == 1, failed.stderr + failed.stdout
    container = latest_suite_container(isolated_cwd)
    assert container.name.endswith("-fail")
    slot = _slot(container, "dry_run_missing_key")
    summary = (slot / "summary.txt").read_text(encoding="utf-8")
    assert "was missing a key" in summary
    assert "col.auto_key()" in summary


@pytest.mark.requirement("E2E-SUITE-12")
def test_cycle_count_repeats_test_sequence(
    core_config,
    fixtures_dir,
    isolated_cwd,
    subprocess_env,
) -> None:
    """cycle_count repeats A, B, C and runs between_tests across the boundary."""
    proc = run_suite_cli(
        _suite(fixtures_dir, "cycle_sequence.toml"),
        core_config,
        isolated_cwd,
        subprocess_env,
    )
    assert proc.returncode == 0, proc.stderr
    container = latest_suite_container(isolated_cwd)
    sequence = (container / "sequence.txt").read_text(encoding="utf-8").splitlines()
    assert sequence == [
        "A",
        "between",
        "B",
        "between",
        "C",
        "between",
        "A",
        "between",
        "B",
        "between",
        "C",
    ]
    summary = read_summary_json(container)
    assert {slot["cycle_index"] for slot in summary["test_slots"]} == {0, 1}
    text = (container / "summary.txt").read_text(encoding="utf-8")
    assert "cycle=0" in text
    assert "cycle=1" in text
    assert len(slot_dirs_matching(container, "cycle_between")) == 5
