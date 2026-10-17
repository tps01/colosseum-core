"""begin_script_slot assigns active mode before the no-artifacts early return."""

from __future__ import annotations

from colosseum.context import init_context
from colosseum.runner.run_options import RunOptions
from colosseum.runner.runtime import begin_script_slot, ensure_suite_runtime_ready


def test_no_artifacts_procedure_applies_only_to_test_phase(core_config) -> None:
    ctx = init_context(
        test_case_name="mode_slot",
        suite_name="mode_slot",
        config_path=core_config,
        no_artifacts=True,
        run_options=RunOptions(execution_mode="procedure"),
    )
    ensure_suite_runtime_ready(ctx, "mode_slot")

    begin_script_slot(ctx, "setup", phase="setup", affects_suite_result=False)
    assert ctx.active_execution_mode == "full"

    begin_script_slot(ctx, "test", phase="test", affects_suite_result=True)
    assert ctx.active_execution_mode == "procedure"

    begin_script_slot(ctx, "teardown", phase="teardown", affects_suite_result=False)
    assert ctx.active_execution_mode == "full"


def test_endex_no_artifacts_suite_does_not_system_exit(core_config) -> None:
    from colosseum.results.exit_policy import endex
    from colosseum.runner.runtime import begin_script_slot, ensure_suite_runtime_ready

    ctx = init_context(
        test_case_name="endex_slot",
        suite_name="endex_slot",
        config_path=core_config,
        no_artifacts=True,
    )
    ensure_suite_runtime_ready(ctx, "endex_slot")
    begin_script_slot(ctx, "pass", phase="test", affects_suite_result=True)
    ctx.slot_script_path = core_config  # any path; finalize uses stem metadata only
    # Must return without raising SystemExit (single-run endex would exit).
    endex()
    assert ctx.slot_finalized is True
    assert ctx.finalized is False
