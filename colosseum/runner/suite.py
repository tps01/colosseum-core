from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from colosseum.paths import absolute_path
from colosseum.runner.provenance import record_suite_provenance
from colosseum.runner.runtime import (
    begin_script_slot,
    ensure_suite_runtime_ready,
    finalize_script_slot,
)
from colosseum.runner.suite_toml import (
    SuiteDefinition,
    SuiteError,
    SuiteTestEntry,
    load_suite_toml,
    parse_repeat_duration,
)

if TYPE_CHECKING:
    from pathlib import Path

    from colosseum.context import RuntimeContext
    from colosseum.runner.run_options import RunOptions

__all__ = [
    "SuiteDefinition",
    "SuiteError",
    "SuiteTestEntry",
    "load_suite_toml",
    "parse_repeat_duration",
    "run_suite",
]


@dataclass(frozen=True)
class _ScriptRunner:
    run: Callable[[Path], None]
    error_type: type[BaseException]


def _stop_remaining_work(ctx: RuntimeContext, test_path: Path, reason: str) -> None:
    """Record fail-fast stop on the session (durable), then best-effort slot DB."""
    ctx.session.mark_fail_fast_stopped(test_path, reason)
    try:
        if ctx.db.is_initialized():
            ctx.db.insert_run_metadata("fail_fast_stopped", "1")
            ctx.db.insert_event("INFO", "runner", f"fail_fast_stop:{test_path}:{reason}")
    except Exception:  # noqa: BLE001 - session stop must survive slot DB errors
        if ctx.logger is not None:
            ctx.logger.exception(
                "fail_fast: could not record stop metadata for %s",
                test_path,
            )
    if ctx.logger is not None:
        ctx.logger.error("fail_fast: stopping remaining tests after %s (%s)", test_path, reason)


def _record_slot_failure(
    suite: SuiteDefinition,
    ctx: RuntimeContext,
    script: Path,
    *,
    phase: str,
    affects_suite_result: bool,
    reason: str,
) -> bool:
    """Score the suite for a failed slot; optionally stop remaining work.

    Supporting-phase failures (setup / between_tests / teardown) always mark
    ``suite_failed``. ``fail_fast`` only controls whether later setup / between /
    test work is skipped (teardown always continues).
    """
    if phase == "setup":
        ctx.session.mark_suite_failed(f"setup_failure:{script}:{reason}")
    elif phase == "between_tests":
        ctx.session.mark_suite_failed(f"between_tests_failure:{script}:{reason}")
    elif phase == "teardown":
        ctx.session.mark_suite_failed(f"teardown_failure:{script}:{reason}")
    elif affects_suite_result:
        label = "slot_start_failed" if reason == "slot_start" else "test_failure"
        ctx.session.mark_suite_failed(f"{label}:{script}:{reason}")
    elif reason == "slot_start":
        ctx.session.mark_suite_failed(f"slot_start_failed:{script}")

    if not suite.fail_fast:
        return False
    if phase == "teardown":
        # Fail the suite but never skip remaining teardown scripts.
        return False
    _stop_remaining_work(ctx, script, reason)
    return True


def _mark_post_endex_slot_failure(ctx: RuntimeContext, script: Path, phase: str) -> None:
    """Update in-memory and on-disk slot result after endex() already finalized."""
    from colosseum.results.aggregation import build_run_summary
    from colosseum.runner.runtime import refresh_slot_artifacts, rename_run_directory_for_result

    ctx.session.mark_suite_failed(f"post_endex_failure:{script}")
    for result in reversed(ctx.suite_slot_results):
        if result.script_path == script and result.phase == phase:
            result.exit_code = 1
            if result.affects_suite_result:
                result.overall = "FAIL"
            if not ctx.no_artifacts and result.output_dir.exists():
                result.output_dir = rename_run_directory_for_result(
                    result.output_dir,
                    "FAIL",
                )
            result.summary = build_run_summary(
                ctx,
                ctx.result_aggregator,
                measurement_count=result.summary.get("measurement_count", 0),
                command_count=result.summary.get("command_count", 0),
            )
            refresh_slot_artifacts(ctx, result)
            break


def _suite_is_cycling(suite: SuiteDefinition) -> bool:
    return suite.cycle_count > 1 or suite.cycle_for is not None


def _cycle_exhausted(
    suite: SuiteDefinition,
    cycle_index: int,
    deadline: float | None,
) -> bool:
    if cycle_index == 0:
        return False
    if suite.cycle_for is not None:
        return deadline is not None and time.monotonic() >= deadline
    return cycle_index >= suite.cycle_count


def _repeat_exhausted(
    entry: SuiteTestEntry,
    repeat_index: int,
    deadline: float | None,
) -> bool:
    if repeat_index == 0:
        return False
    if entry.repeat_for is not None:
        return deadline is not None and time.monotonic() >= deadline
    return repeat_index >= entry.repeat_count


def _attach_slot_parameters(
    suite: SuiteDefinition,
    ctx: RuntimeContext,
    script: Path,
    *,
    phase: str,
    entry: SuiteTestEntry | None,
) -> bool:
    """Attach parameters for one slot. Returns False when load failed."""
    from colosseum.config.parameters import (
        ParametersError,
        _attach_parameter_sources,
        _suite_parameter_paths,
        attach_parameters,
    )

    entry_parameters = entry.parameters if entry is not None else None
    suite_level = ctx.run_options.parameters_path if ctx.run_options.parameters_path is not None else suite.parameters
    try:
        sources = _suite_parameter_paths(
            script_path=script if phase == "test" else None,
            entry_path=entry_parameters if phase == "test" else None,
            suite_path=suite_level,
            stacking=phase == "test" and suite.parameter_stacking,
        )
        if len(sources) > 1:
            _attach_parameter_sources(ctx, sources)
        else:
            attach_parameters(
                ctx,
                sources[0] if sources else None,
                required=suite_level is not None or (phase == "test" and entry_parameters is not None),
            )
    except ParametersError as exc:
        ctx.result_aggregator.mark_suite_error(str(exc))
        if ctx.logger is not None:
            ctx.logger.error("Parameters load failed: %s", exc)
        return False
    return True


def _insert_repeat_metadata(
    ctx: RuntimeContext,
    script: Path,
    *,
    test_index: int,
    repeat_index: int,
    cycle_index: int | None,
    entry: SuiteTestEntry,
) -> None:
    repeat_meta = {
        "test_index": str(test_index),
        "test_repeat_index": str(repeat_index),
    }
    if cycle_index is not None:
        repeat_meta["cycle_index"] = str(cycle_index)
    if entry.repeat_for is not None:
        repeat_meta.update(
            repeat_mode="duration",
            repeat_limit=str(int(entry.repeat_for.total_seconds())),
        )
    elif entry.repeat_count > 1:
        repeat_meta.update(
            repeat_mode="count",
            repeat_limit=str(entry.repeat_count),
        )
    for key, value in repeat_meta.items():
        ctx.db.insert_run_metadata(key, value)
    ctx.db.insert_event(
        "INFO",
        "runner",
        f"test_repeat_start:{script}:test={test_index}:repeat={repeat_index}",
    )


def _invoke_slot_script(
    ctx: RuntimeContext,
    script: Path,
    runner: _ScriptRunner,
    *,
    phase: str,
) -> bool:
    """Run the slot script. Returns True when the script crashed."""
    try:
        runner.run(script)
    except runner.error_type:
        ctx.result_aggregator.mark_suite_error(f"{phase} script failed")
        if ctx.slot_finalized:
            _mark_post_endex_slot_failure(ctx, script, phase)
        return True
    return False


def _run_script_slot(
    suite: SuiteDefinition,
    ctx: RuntimeContext,
    script: Path,
    runner: _ScriptRunner,
    *,
    phase: str,
    affects_suite_result: bool,
    test_index: int | None = None,
    repeat_index: int | None = None,
    cycle_index: int | None = None,
    entry: SuiteTestEntry | None = None,
) -> bool:
    """Run one script slot. Returns True when fail_fast should stop non-teardown work."""
    slot_started = False
    try:
        begin_script_slot(
            ctx,
            script.stem,
            phase=phase,
            affects_suite_result=affects_suite_result,
        )
        slot_started = True
    except Exception as exc:  # noqa: BLE001 - continue suite; signals propagate
        if ctx.logger is not None:
            ctx.logger.exception("Script slot start failed for %s: %s", script, exc)
        return _record_slot_failure(
            suite,
            ctx,
            script,
            phase=phase,
            affects_suite_result=affects_suite_result,
            reason="slot_start",
        )

    ctx.slot_script_path = script
    ctx.slot_test_index = test_index
    ctx.slot_repeat_index = repeat_index
    ctx.slot_cycle_index = cycle_index

    script_crash = False
    stop_fail_fast = False
    try:
        params_ok = _attach_slot_parameters(
            suite,
            ctx,
            script,
            phase=phase,
            entry=entry,
        )
        if not params_ok:
            script_crash = True
        else:
            if test_index is not None and repeat_index is not None and entry is not None:
                _insert_repeat_metadata(
                    ctx,
                    script,
                    test_index=test_index,
                    repeat_index=repeat_index,
                    cycle_index=cycle_index,
                    entry=entry,
                )
            script_crash = _invoke_slot_script(ctx, script, runner, phase=phase)

        slot_has_failure = script_crash or not ctx.result_aggregator.overall_pass()
        if slot_has_failure:
            reason = "script_error" if script_crash else "required_failure"
            stop_fail_fast = _record_slot_failure(
                suite,
                ctx,
                script,
                phase=phase,
                affects_suite_result=affects_suite_result,
                reason=reason,
            )
    except Exception as exc:  # noqa: BLE001 - finalize slot; signals propagate
        if ctx.logger is not None:
            ctx.logger.exception("Script slot failed for %s: %s", script, exc)
        ctx.result_aggregator.mark_suite_error(f"{phase} slot failed: {exc}")
        stop_fail_fast = _record_slot_failure(
            suite,
            ctx,
            script,
            phase=phase,
            affects_suite_result=affects_suite_result,
            reason="slot_error",
        )
    finally:
        if slot_started and not ctx.slot_finalized:
            finalize_script_slot(
                ctx,
                script_path=script,
                test_index=test_index,
                repeat_index=repeat_index,
                cycle_index=cycle_index,
            )
    return stop_fail_fast


def _run_phase_scripts(
    suite: SuiteDefinition,
    ctx: RuntimeContext,
    scripts: list[Path],
    runner: _ScriptRunner,
    *,
    phase: str,
    affects_suite_result: bool,
    stop_on_fail_fast: bool,
) -> bool:
    """Run phase scripts. Returns True if fail_fast should stop non-teardown work.

    Teardown always runs every script (``stop_on_fail_fast=False``).
    """
    stopped = False
    for script in scripts:
        stop = _run_script_slot(
            suite,
            ctx,
            script,
            runner,
            phase=phase,
            affects_suite_result=affects_suite_result,
        )
        if stop and stop_on_fail_fast:
            return True
        if stop:
            stopped = True
    return stopped and stop_on_fail_fast


def _run_test_schedule(
    suite: SuiteDefinition,
    ctx: RuntimeContext,
    runner: _ScriptRunner,
) -> bool:
    cycling = _suite_is_cycling(suite)
    cycle_deadline = time.monotonic() + suite.cycle_for.total_seconds() if suite.cycle_for is not None else None
    cycle_index = 0
    while not _cycle_exhausted(suite, cycle_index, cycle_deadline):
        recorded_cycle = cycle_index if cycling else None
        for test_index, entry in enumerate(suite.tests):
            entry_deadline = (
                time.monotonic() + entry.repeat_for.total_seconds() if entry.repeat_for is not None else None
            )
            repeat_index = 0
            while not _repeat_exhausted(entry, repeat_index, entry_deadline):
                stop = _run_script_slot(
                    suite,
                    ctx,
                    entry.path,
                    runner,
                    phase="test",
                    affects_suite_result=True,
                    test_index=test_index,
                    repeat_index=repeat_index,
                    cycle_index=recorded_cycle,
                    entry=entry,
                )
                repeat_index += 1
                if stop:
                    return True
                if entry.repeat_for is not None:
                    another_in_entry = entry_deadline is not None and time.monotonic() < entry_deadline
                else:
                    another_in_entry = repeat_index < entry.repeat_count
                another_test = test_index + 1 < len(suite.tests)
                another_cycle = not _cycle_exhausted(suite, cycle_index + 1, cycle_deadline)
                if (another_in_entry or another_test or another_cycle) and suite.between_tests:
                    between_stop = _run_phase_scripts(
                        suite,
                        ctx,
                        suite.between_tests,
                        runner,
                        phase="between_tests",
                        affects_suite_result=False,
                        stop_on_fail_fast=True,
                    )
                    if between_stop:
                        return True
                if not another_in_entry:
                    break
        cycle_index += 1
    return False


def _bootstrap_suite(
    suite_path: Path,
    config_path: Path | None,
    metadata_path: Path | None,
    *,
    debug: bool,
    no_artifacts: bool,
    run_options: RunOptions | None,
) -> tuple[SuiteDefinition, RuntimeContext, _ScriptRunner]:
    from colosseum.config import load_config
    from colosseum.config.metadata import load_metadata
    from colosseum.context import get_context, init_context
    from colosseum.results.reports import apply_enabled_reports
    from colosseum.runner.run_options import RunOptions

    from .single_test import ScriptRunError, run_script

    suite = load_suite_toml(suite_path)
    options = run_options or RunOptions()
    init_context(
        test_case_name=suite.name,
        suite_name=suite.name,
        config_path=absolute_path(config_path) if config_path else None,
        metadata_path=absolute_path(metadata_path) if metadata_path else None,
        no_artifacts=no_artifacts,
        run_options=options,
    )
    ctx = get_context()
    ctx.debug_logging = debug
    if config_path:
        load_config(config_path, metadata_path=metadata_path)
        ctx.session.config_pinned = True
        if metadata_path:
            ctx.session.metadata_pinned = True
    elif metadata_path:
        load_metadata(metadata_path)
        ctx.session.metadata_pinned = True

    apply_enabled_reports(ctx)
    ensure_suite_runtime_ready(ctx, suite.name)
    suite_level = options.parameters_path if options.parameters_path is not None else suite.parameters
    record_suite_provenance(
        ctx,
        suite_path=suite_path,
        setup=suite.setup,
        tests=[(entry.path, entry.parameters) for entry in suite.tests],
        between_tests=suite.between_tests,
        teardown=suite.teardown,
        suite_parameters=suite_level,
        parameter_stacking=suite.parameter_stacking,
    )
    runner = _ScriptRunner(run_script, ScriptRunError)
    if ctx.logger is not None:
        ctx.logger.debug(
            "Suite %r: setup=%d tests=%d between=%d teardown=%d fail_fast=%s "
            "cycle_count=%d cycle_for=%s parameter_stacking=%s",
            suite.name,
            len(suite.setup),
            len(suite.tests),
            len(suite.between_tests),
            len(suite.teardown),
            suite.fail_fast,
            suite.cycle_count,
            suite.cycle_for,
            suite.parameter_stacking,
        )
    return suite, ctx, runner


def _run_suite_body(
    suite: SuiteDefinition,
    ctx: RuntimeContext,
    runner: _ScriptRunner,
) -> BaseException | None:
    """Run setup and the test schedule. Returns a deferred interrupt, if any."""
    interrupt: BaseException | None = None
    try:
        stop = False
        if suite.setup:
            stop = _run_phase_scripts(
                suite,
                ctx,
                suite.setup,
                runner,
                phase="setup",
                affects_suite_result=False,
                stop_on_fail_fast=True,
            )
        if not stop:
            _run_test_schedule(suite, ctx, runner)
    except Exception as exc:  # noqa: BLE001 - still tear down and finalize
        if ctx.logger is not None:
            ctx.logger.exception("Suite execution failed: %s", exc)
        ctx.session.mark_suite_failed(f"suite_crash:{exc}")
    except BaseException as exc:
        interrupt = exc
        if ctx.logger is not None:
            ctx.logger.exception("Suite execution interrupted: %s", exc)
        ctx.session.mark_suite_failed(f"suite_interrupt:{exc}")
    return interrupt


def _run_suite_teardown(
    suite: SuiteDefinition,
    ctx: RuntimeContext,
    runner: _ScriptRunner,
) -> None:
    try:
        if suite.teardown:
            _run_phase_scripts(
                suite,
                ctx,
                suite.teardown,
                runner,
                phase="teardown",
                affects_suite_result=False,
                stop_on_fail_fast=False,
            )
    except Exception as exc:  # noqa: BLE001 - finalize anyway
        if ctx.logger is not None:
            ctx.logger.exception("Suite teardown failed: %s", exc)


def run_suite(
    suite_path: Path,
    config_path: Path | None = None,
    metadata_path: Path | None = None,
    *,
    debug: bool = False,
    no_artifacts: bool = False,
    run_options: RunOptions | None = None,
) -> int:
    from colosseum.results.exit_policy import finalize_suite

    suite, ctx, runner = _bootstrap_suite(
        suite_path,
        config_path,
        metadata_path,
        debug=debug,
        no_artifacts=no_artifacts,
        run_options=run_options,
    )

    interrupt: BaseException | None = None
    try:
        interrupt = _run_suite_body(suite, ctx, runner)
    finally:
        _run_suite_teardown(suite, ctx, runner)
        code = finalize_suite(ctx)

    if interrupt is not None:
        raise interrupt
    raise SystemExit(code)
