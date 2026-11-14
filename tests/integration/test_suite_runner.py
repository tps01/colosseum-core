"""I-SUITE: run_suite phase behavior."""

from __future__ import annotations

import json

import pytest

from colosseum.runner.suite import run_suite
from tests.support.helpers import (
    latest_suite_container,
    query_db,
    slot_dirs_matching,
)


def _run_suite_expect_exit(suite_path, core_config, isolated_cwd, code: int) -> None:
    with pytest.raises(SystemExit) as exc:
        run_suite(suite_path, core_config)
    assert exc.value.code == code


def _container_summary(container) -> dict:
    path = container / "summary.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _slot_with_stem(container, stem: str):
    matches = slot_dirs_matching(container, stem)
    assert matches, f"no slot dir matching {stem!r} under {container}"
    return matches[-1]


def test_post_endex_decorator_does_not_leave_sibling_outputs(
    fixtures_dir,
    core_config,
    isolated_cwd,
) -> None:
    """A decorated call after endex() must not mint an unmarked outputs sibling."""
    suite = fixtures_dir / "suites" / "endex_then_verify.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 1)
    outputs = isolated_cwd / "outputs"
    dirs = sorted(path for path in outputs.iterdir() if path.is_dir())
    assert len(dirs) == 1
    container = dirs[0]
    assert container.name.endswith("-fail")
    assert (container / "debug.log").is_file()
    assert (container / "summary.txt").is_file()
    assert (container / "execution.sqlite").is_file()
    unmarked = [path for path in dirs if not path.name.endswith(("-pass", "-fail"))]
    assert unmarked == []
    slot = _slot_with_stem(container, "endex_then_verify")
    assert json.loads((slot / "summary.json").read_text())["exit_code"] == 1
    metadata = dict(query_db(slot, "SELECT key,value FROM run_metadata"))
    assert metadata["overall_status"] == "FAIL"
    assert metadata["exit_code"] == "1"
    stored = query_db(slot, "SELECT overall_result,exit_code FROM run_result")
    assert stored == [("FAIL", 1)]
    manifest = query_db(container, "SELECT overall_result,exit_code FROM suite_slot_results")
    assert manifest == [("FAIL", 1)]


@pytest.mark.parametrize("no_artifacts", [False, True])
def test_suite_requirements_use_completed_facts_in_both_storage_modes(
    isolated_cwd,
    core_config,
    capsys,
    no_artifacts,
):
    from colosseum.context import get_context

    script = isolated_cwd / "check.py"
    script.write_text(
        "from colosseum.decorators import verification\n"
        "@verification\n"
        "def check(*, key): return False\n"
        "def main(): check(key='v', requirements=['REQ-1'], optional=True)\n",
        encoding="utf-8",
    )
    support = isolated_cwd / "setup.py"
    support.write_text(script.read_text().replace("REQ-1", "SUPPORT-ONLY"), encoding="utf-8")
    suite = isolated_cwd / "suite.toml"
    suite.write_text(
        'name="requirements"\nsetup=["setup.py"]\ntests=[{path="check.py", repeat_count=2}]\n',
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exc:
        run_suite(suite, core_config, no_artifacts=no_artifacts)
    assert exc.value.code == 0  # Optional failures retain their existing exit policy.
    ctx = get_context()
    assert len(ctx.suite_slot_results) == 3
    assert len(ctx.suite_test_results) == 2
    assert "REQ-1: FAIL" in capsys.readouterr().out
    if no_artifacts:
        assert not (isolated_cwd / "outputs").exists()
    else:
        container = ctx.suite_output_dir
        summary = _container_summary(container)
        assert [row["id"] for row in summary["requirements"]] == ["REQ-1"]
        assert len(summary["requirements"][0]["failures"]) == 2
        saved = query_db(container, "SELECT payload_json FROM run_result")
        assert json.loads(saved[0][0]) == summary
        slots = query_db(container, "SELECT slot_id,output_directory FROM suite_slot_results ORDER BY slot_id")
        assert [row[0] for row in slots] == [0, 1, 2]
        assert all((container / row[1]).is_dir() for row in slots)


def test_default_continues_after_test_crash(fixtures_dir, core_config, isolated_cwd) -> None:
    suite = fixtures_dir / "suites" / "multi_test_continue.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 1)
    container = latest_suite_container(isolated_cwd)
    assert len(slot_dirs_matching(container, "crash_test")) == 1
    assert len(slot_dirs_matching(container, "pass_test")) == 1
    assert _slot_with_stem(container, "teardown_ok")
    summary = _container_summary(container)
    assert len(summary["test_slots"]) == 2


def test_suite_finalizes_when_directory_rename_fails(
    fixtures_dir,
    core_config,
    isolated_cwd,
    monkeypatch,
) -> None:
    """Rename failures must not skip suite summary or tear down (#72)."""
    from pathlib import Path

    import colosseum.results.exit_policy as exit_policy
    import colosseum.results.finalize as finalize_mod

    def keep_unrenamed(output_dir: Path, overall: str, **_kwargs: object) -> Path:
        return output_dir

    monkeypatch.setattr(finalize_mod, "rename_run_directory_for_result", keep_unrenamed)
    monkeypatch.setattr(exit_policy, "rename_run_directory_for_result", keep_unrenamed)

    suite = fixtures_dir / "suites" / "happy.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 0)
    container = latest_suite_container(isolated_cwd)
    assert not container.name.endswith(("-pass", "-fail"))
    assert (container / "summary.txt").is_file()
    assert (container / "summary.json").is_file()
    assert (container / "debug.log").is_file()
    test_slot = _slot_with_stem(container, "pass_test")
    assert not test_slot.name.endswith(("-pass", "-fail"))
    assert (test_slot / "summary.txt").is_file()
    summary = _container_summary(container)
    assert summary["overall_result"] == "PASS"


def test_fail_fast_stops_after_required_verification_fail(fixtures_dir, core_config, isolated_cwd) -> None:
    suite = fixtures_dir / "suites" / "multi_test_fail_fast_verify.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 1)
    container = latest_suite_container(isolated_cwd)
    assert len(slot_dirs_matching(container, "fail_required_verify")) == 1
    assert slot_dirs_matching(container, "pass_test") == []
    fail_slot = _slot_with_stem(container, "fail_required_verify")
    meta = dict(query_db(fail_slot, "SELECT key, value FROM run_metadata"))
    assert meta.get("fail_fast_stopped") == "1"


def test_repeat_for_runs_until_deadline(fixtures_dir, core_config, isolated_cwd) -> None:
    suite = fixtures_dir / "suites" / "repeat_for.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 0)
    container = latest_suite_container(isolated_cwd)
    assert len(slot_dirs_matching(container, "count_repeat")) >= 2


def test_repeat_failure_continues_when_fail_fast_false(fixtures_dir, core_config, isolated_cwd) -> None:
    suite = fixtures_dir / "suites" / "repeat_fail_continue.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 1)
    container = latest_suite_container(isolated_cwd)
    assert len(slot_dirs_matching(container, "repeat_fail_first")) == 3


def test_repeat_failure_stops_when_fail_fast_true(fixtures_dir, core_config, isolated_cwd) -> None:
    suite = fixtures_dir / "suites" / "repeat_fail_fast.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 1)
    container = latest_suite_container(isolated_cwd)
    assert len(slot_dirs_matching(container, "repeat_fail_first")) == 1


def test_between_tests_crash_continues_when_fail_fast_false(fixtures_dir, core_config, isolated_cwd) -> None:
    suite = fixtures_dir / "suites" / "between_crash_continue.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 1)
    container = latest_suite_container(isolated_cwd)
    assert len(slot_dirs_matching(container, "pass_test")) == 2
    assert _slot_with_stem(container, "crash_test")
    summary = _container_summary(container)
    assert summary["overall_result"] == "FAIL"
    assert summary["suite_failed"] is True
    assert summary["fail_fast_stopped"] is False


def test_suite_shutdown_hook_runs_once(fixtures_dir, core_config, isolated_cwd) -> None:
    """Plugin shutdown hooks run once at suite finalize, not per slot."""
    from colosseum.context import get_context
    from colosseum.plugins.registry import PluginRegistry

    suite = fixtures_dir / "suites" / "happy.toml"
    hooks = {"count": 0}
    original_init = PluginRegistry.__init__

    def _counting_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.register_shutdown(lambda: hooks.__setitem__("count", hooks["count"] + 1))

    PluginRegistry.__init__ = _counting_init  # type: ignore[method-assign]
    try:
        with pytest.raises(SystemExit) as exc:
            run_suite(suite, core_config)
        assert exc.value.code == 0
    finally:
        PluginRegistry.__init__ = original_init  # type: ignore[method-assign]
    assert hooks["count"] == 1
    # Context still reachable until next init; suite finalized.
    assert get_context().suite_finalized is True


def test_no_artifacts_suite_endex_finalizes_slot_only(
    fixtures_dir,
    core_config,
    isolated_cwd,
) -> None:
    """no-artifacts suite: endex() must not exit the process (session.kind=suite)."""
    suite = fixtures_dir / "suites" / "no_artifacts_endex.toml"
    with pytest.raises(SystemExit) as exc:
        run_suite(suite, core_config, no_artifacts=True)
    assert exc.value.code == 0
    assert not (isolated_cwd / "outputs").exists()


def _verification_outcomes(summary: dict) -> int:
    return sum(1 for row in summary.get("outcomes", []) if row.get("kind") == "verification")


def test_no_artifacts_suite_procedure_skips_test_verifications(
    fixtures_dir,
    core_config,
    isolated_cwd,
) -> None:
    """Procedure mode skips test verifications and still runs them in other phases."""
    from colosseum.context import get_context
    from colosseum.runner.run_options import RunOptions

    suite = fixtures_dir / "suites" / "no_artifacts_procedure.toml"
    with pytest.raises(SystemExit) as exc:
        run_suite(
            suite,
            core_config,
            no_artifacts=True,
            run_options=RunOptions(execution_mode="procedure"),
        )
    assert exc.value.code == 0
    assert not (isolated_cwd / "outputs").exists()
    slots = {slot.phase: slot for slot in get_context().suite_slot_results}
    assert list(slots) == ["setup", "test", "teardown"]
    assert _verification_outcomes(slots["setup"].summary) == 1
    assert _verification_outcomes(slots["test"].summary) == 0
    assert slots["test"].summary["measurement_count"] >= 1
    assert _verification_outcomes(slots["teardown"].summary) == 1


def _sequence(container) -> list[str]:
    return (container / "sequence.txt").read_text(encoding="utf-8").splitlines()


def test_cycle_count_keeps_inner_repeats_together(
    fixtures_dir,
    core_config,
    isolated_cwd,
) -> None:
    suite = fixtures_dir / "suites" / "cycle_nested_repeat.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 0)
    container = latest_suite_container(isolated_cwd)
    assert _sequence(container) == ["A", "A", "B", "A", "A", "B"]


def test_cycle_fail_fast_stops_rest_of_cycle_and_later_cycles(
    fixtures_dir,
    core_config,
    isolated_cwd,
) -> None:
    suite = fixtures_dir / "suites" / "cycle_fail_fast.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 1)
    container = latest_suite_container(isolated_cwd)
    assert len(slot_dirs_matching(container, "cycle_a")) == 1
    assert len(slot_dirs_matching(container, "crash_test")) == 1
    assert slot_dirs_matching(container, "cycle_c") == []
    assert _slot_with_stem(container, "teardown_ok")


def test_teardown_continues_when_later_slot_start_fails(
    fixtures_dir,
    core_config,
    isolated_cwd,
    monkeypatch,
) -> None:
    """A teardown that never starts must not skip remaining teardown scripts."""
    import colosseum.runner.suite as suite_mod

    real_begin = suite_mod.begin_script_slot

    def begin(ctx, logical_name, *, phase, affects_suite_result):  # noqa: ANN001
        if phase == "teardown" and logical_name == "teardown_ok_b":
            raise OSError("induced teardown slot start failure")
        return real_begin(
            ctx,
            logical_name,
            phase=phase,
            affects_suite_result=affects_suite_result,
        )

    monkeypatch.setattr(suite_mod, "begin_script_slot", begin)
    suite = fixtures_dir / "suites" / "teardown_triple.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 1)
    container = latest_suite_container(isolated_cwd)
    assert _slot_with_stem(container, "teardown_ok")
    assert slot_dirs_matching(container, "teardown_ok_b") == []
    assert _slot_with_stem(container, "teardown_ok_c")
    summary = _container_summary(container)
    assert summary["overall_result"] == "FAIL"
    assert summary["suite_failed"] is True


def test_test_slot_start_failure_continues_later_tests(
    fixtures_dir,
    core_config,
    isolated_cwd,
    monkeypatch,
) -> None:
    """fail_fast=false: a test that never starts fails the suite but later work runs."""
    import colosseum.runner.suite as suite_mod

    real_begin = suite_mod.begin_script_slot

    def begin(ctx, logical_name, *, phase, affects_suite_result):  # noqa: ANN001
        if phase == "test" and logical_name == "pass_test_b":
            raise OSError("induced test slot start failure")
        return real_begin(
            ctx,
            logical_name,
            phase=phase,
            affects_suite_result=affects_suite_result,
        )

    monkeypatch.setattr(suite_mod, "begin_script_slot", begin)
    suite = fixtures_dir / "suites" / "three_test_continue.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 1)
    container = latest_suite_container(isolated_cwd)
    assert _slot_with_stem(container, "pass_test")
    assert slot_dirs_matching(container, "pass_test_b") == []
    assert _slot_with_stem(container, "crash_test")
    assert _slot_with_stem(container, "teardown_ok")
    summary = _container_summary(container)
    assert summary["overall_result"] == "FAIL"
    assert summary["suite_failed"] is True


def test_reattach_console_failure_continues_schedule(
    fixtures_dir,
    core_config,
    isolated_cwd,
    monkeypatch,
) -> None:
    """Console reattach after a slot must not abort the rest of the suite."""
    import colosseum.logging.setup as logging_setup

    original = logging_setup.attach_console_logger
    state = {"n": 0}

    def boom(ctx, *, console_level=20):  # noqa: ANN001
        state["n"] += 1
        if state["n"] == 1:
            raise OSError("induced console reattach failure")
        return original(ctx, console_level=console_level)

    monkeypatch.setattr(logging_setup, "attach_console_logger", boom)
    suite = fixtures_dir / "suites" / "multi_test_continue.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 1)
    container = latest_suite_container(isolated_cwd)
    assert _slot_with_stem(container, "crash_test")
    assert _slot_with_stem(container, "pass_test")
    assert _slot_with_stem(container, "teardown_ok")
    summary = _container_summary(container)
    assert len(summary["test_slots"]) == 2


def test_fail_fast_metadata_write_failure_still_finalizes_slot(
    fixtures_dir,
    core_config,
    isolated_cwd,
    monkeypatch,
) -> None:
    """fail_fast DB metadata errors must not skip slot finalize or teardown."""
    from colosseum.database.manager import DatabaseManager

    original = DatabaseManager.insert_run_metadata

    def wrapped(self, key, value):  # noqa: ANN001
        if key == "fail_fast_stopped":
            raise OSError("induced fail_fast metadata failure")
        return original(self, key, value)

    monkeypatch.setattr(DatabaseManager, "insert_run_metadata", wrapped)
    suite = fixtures_dir / "suites" / "multi_test_fail_fast_crash.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 1)
    container = latest_suite_container(isolated_cwd)
    crash_slot = _slot_with_stem(container, "crash_test")
    assert (crash_slot / "summary.json").is_file()
    assert _slot_with_stem(container, "teardown_ok")
    summary = _container_summary(container)
    assert summary["overall_result"] == "FAIL"
    assert summary["fail_fast_stopped"] is True
    assert len(summary["test_slots"]) == 1


def test_suite_summary_write_failure_still_exits_with_code(
    fixtures_dir,
    core_config,
    isolated_cwd,
    monkeypatch,
) -> None:
    from colosseum.context import get_context
    from colosseum.summary.writer import SuiteSummaryWriter

    def boom(self, *args, **kwargs):  # noqa: ANN001
        raise OSError("induced suite summary write failure")

    monkeypatch.setattr(SuiteSummaryWriter, "write", boom)
    suite = fixtures_dir / "suites" / "happy.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 0)
    assert get_context().suite_finalized is True
    container = latest_suite_container(isolated_cwd)
    assert not (container / "summary.json").is_file()
    assert _slot_with_stem(container, "teardown_ok")


def test_suite_logger_close_failure_still_writes_summary(
    fixtures_dir,
    core_config,
    isolated_cwd,
    monkeypatch,
) -> None:
    import colosseum.results.exit_policy as exit_policy

    def boom(logger):  # noqa: ANN001
        raise OSError("induced suite logger close failure")

    monkeypatch.setattr(exit_policy, "close_logger_handlers", boom)
    suite = fixtures_dir / "suites" / "happy.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 0)
    container = latest_suite_container(isolated_cwd)
    assert (container / "summary.json").is_file()
    assert _container_summary(container)["overall_result"] == "PASS"


def test_endex_then_raise_fails_suite_and_continues(
    fixtures_dir,
    core_config,
    isolated_cwd,
) -> None:
    suite = fixtures_dir / "suites" / "endex_then_raise.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 1)
    container = latest_suite_container(isolated_cwd)
    first = _slot_with_stem(container, "endex_then_raise")
    # Post-endex failure re-stamps the slot folder to match suite FAIL.
    assert first.name.endswith("-fail")
    second = _slot_with_stem(container, "pass_test")
    assert second.name.endswith("-pass")
    for slot_dir in (first, second):
        slot_summary = _container_summary(slot_dir)
        assert slot_summary["start_time_utc"]
        assert slot_summary["duration_seconds"] >= 0
        assert "Runtime:" in (slot_dir / "summary.txt").read_text(encoding="utf-8")
    assert _slot_with_stem(container, "teardown_ok")
    summary = _container_summary(container)
    assert summary["overall_result"] == "FAIL"
    assert summary["suite_failed"] is True
    assert any(slot["exit_code"] == 1 for slot in summary["test_slots"])
    assert any(
        str(slot["script"]).endswith("endex_then_raise.py") and slot["overall_result"] == "FAIL"
        for slot in summary["test_slots"]
    )


def test_endex_then_systemexit_1_fails_suite(
    fixtures_dir,
    core_config,
    isolated_cwd,
) -> None:
    suite = fixtures_dir / "suites" / "endex_then_systemexit_1.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 1)
    container = latest_suite_container(isolated_cwd)
    assert _slot_with_stem(container, "pass_test")
    assert _container_summary(container)["overall_result"] == "FAIL"


def test_endex_then_systemexit_0_keeps_suite_pass(
    fixtures_dir,
    core_config,
    isolated_cwd,
) -> None:
    suite = fixtures_dir / "suites" / "endex_then_systemexit_0.toml"
    _run_suite_expect_exit(suite, core_config, isolated_cwd, 0)
    container = latest_suite_container(isolated_cwd)
    assert _container_summary(container)["overall_result"] == "PASS"


def test_fail_fast_setup_missing_parameters_fails_suite(
    fixtures_dir,
    core_config,
    isolated_cwd,
    tmp_path,
) -> None:
    from colosseum.runner.run_options import RunOptions

    missing = tmp_path / "missing-parameters.toml"
    suite_path = tmp_path / "ff_setup_params.toml"
    setup = (fixtures_dir / "scripts" / "setup_ok.py").resolve().as_posix()
    test = (fixtures_dir / "scripts" / "pass_test.py").resolve().as_posix()
    teardown = (fixtures_dir / "scripts" / "teardown_ok.py").resolve().as_posix()
    suite_path.write_text(
        "\n".join(
            [
                'name = "ff_setup_params"',
                "fail_fast = true",
                f'setup = ["{setup}"]',
                f'tests = ["{test}"]',
                f'teardown = ["{teardown}"]',
                "",
            ],
        ),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exc:
        run_suite(
            suite_path,
            core_config,
            run_options=RunOptions(parameters_path=missing),
        )
    assert exc.value.code == 1
    container = latest_suite_container(isolated_cwd)
    assert _slot_with_stem(container, "setup_ok")
    assert slot_dirs_matching(container, "pass_test") == []
    assert _slot_with_stem(container, "teardown_ok")
    summary = _container_summary(container)
    assert summary["overall_result"] == "FAIL"
    assert summary["fail_fast_stopped"] is True


def test_keyboard_interrupt_in_teardown_propagates(
    fixtures_dir,
    core_config,
    isolated_cwd,
) -> None:
    """KeyboardInterrupt from teardown must not be turned into SystemExit."""
    suite = fixtures_dir / "suites" / "teardown_kb_interrupt.toml"
    with pytest.raises(KeyboardInterrupt, match="induced in teardown"):
        run_suite(suite, core_config)
    container = latest_suite_container(isolated_cwd)
    assert _slot_with_stem(container, "pass_test")
    assert _slot_with_stem(container, "teardown_keyboard_interrupt")
    # Later teardown is skipped; suite summary is not written (Python default unwind).
    assert slot_dirs_matching(container, "teardown_ok") == []
    assert not (container / "summary.json").is_file()


def _write_parameter_probe(tmp_path) -> tuple:
    script = tmp_path / "param_probe.py"
    script.write_text(
        "\n".join(
            [
                "from colosseum.config.parameters import load_parameter",
                "from colosseum.context import get_context",
                "",
                "",
                "def main() -> None:",
                "    ctx = get_context()",
                "    payload = {",
                '        "voltage": load_parameter("voltage", field="limit"),',
                '        "current": load_parameter("current", field="limit"),',
                '        "missing": load_parameter("missing", field="limit"),',
                "    }",
                '    (ctx.output_dir / "params.json").write_text(',
                "        __import__('json').dumps(payload),",
                "        encoding='utf-8',",
                "    )",
                "",
            ],
        ),
        encoding="utf-8",
    )
    suite_limits = tmp_path / "suite_limits.toml"
    suite_limits.write_text('[current]\nlimit = "3A"\n', encoding="utf-8")
    test_limits = tmp_path / "test_limits.toml"
    test_limits.write_text(
        '[voltage]\nlimit = "5V"\n\n[current]\nlimit = "5A"\n',
        encoding="utf-8",
    )
    cli_limits = tmp_path / "cli_limits.toml"
    cli_limits.write_text('[current]\nlimit = "1A"\n', encoding="utf-8")
    return script, suite_limits, test_limits, cli_limits


def test_suite_parameter_stacking_default_merges(
    core_config,
    isolated_cwd,
    tmp_path,
) -> None:
    script, suite_limits, test_limits, _cli = _write_parameter_probe(tmp_path)
    suite_path = tmp_path / "stack_default.toml"
    suite_path.write_text(
        "\n".join(
            [
                'name = "stack_default"',
                f'parameters = "{suite_limits.name}"',
                "tests = [",
                f'  {{ path = "{script.name}", parameters = "{test_limits.name}" }},',
                "]",
                "",
            ],
        ),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exc:
        run_suite(suite_path, core_config)
    assert exc.value.code == 0
    slot = _slot_with_stem(latest_suite_container(isolated_cwd), "param_probe")
    payload = json.loads((slot / "params.json").read_text(encoding="utf-8"))
    assert payload == {"voltage": "5V", "current": "3A", "missing": None}


def test_suite_parameter_cli_overrides_suite_toml_path(
    core_config,
    isolated_cwd,
    tmp_path,
) -> None:
    from colosseum.runner.run_options import RunOptions

    script, suite_limits, test_limits, cli_limits = _write_parameter_probe(tmp_path)
    suite_path = tmp_path / "stack_cli.toml"
    suite_path.write_text(
        "\n".join(
            [
                'name = "stack_cli"',
                f'parameters = "{suite_limits.name}"',
                "tests = [",
                f'  {{ path = "{script.name}", parameters = "{test_limits.name}" }},',
                "]",
                "",
            ],
        ),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exc:
        run_suite(
            suite_path,
            core_config,
            run_options=RunOptions(parameters_path=cli_limits),
        )
    assert exc.value.code == 0
    slot = _slot_with_stem(latest_suite_container(isolated_cwd), "param_probe")
    payload = json.loads((slot / "params.json").read_text(encoding="utf-8"))
    assert payload == {"voltage": "5V", "current": "1A", "missing": None}


def test_suite_parameter_stacking_false_excludes_test_file(
    core_config,
    isolated_cwd,
    tmp_path,
) -> None:
    script, suite_limits, test_limits, _cli = _write_parameter_probe(tmp_path)
    suite_path = tmp_path / "stack_off.toml"
    suite_path.write_text(
        "\n".join(
            [
                'name = "stack_off"',
                f'parameters = "{suite_limits.name}"',
                "parameter_stacking = false",
                "tests = [",
                f'  {{ path = "{script.name}", parameters = "{test_limits.name}" }},',
                "]",
                "",
            ],
        ),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exc:
        run_suite(suite_path, core_config)
    assert exc.value.code == 0
    slot = _slot_with_stem(latest_suite_container(isolated_cwd), "param_probe")
    payload = json.loads((slot / "params.json").read_text(encoding="utf-8"))
    assert payload == {"voltage": None, "current": "3A", "missing": None}
