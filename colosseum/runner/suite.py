from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Callable

from colosseum.config.toml_relaxed import coerce_config_bool, read_relaxed_toml
from colosseum.runner.provenance import record_suite_provenance
from colosseum.runner.runtime import (
    begin_script_slot,
    ensure_suite_runtime_ready,
    finalize_script_slot,
)

if TYPE_CHECKING:
    from pathlib import Path

    from colosseum.context import RuntimeContext
    from colosseum.runner.run_options import RunOptions

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

_DURATION_RE = re.compile(
    r"^(?:(?P<days>\d+)d)?(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+)s?)?$",
    re.IGNORECASE,
)


@dataclass
class SuiteTestEntry:
    path: Path
    repeat_count: int = 1
    repeat_for: timedelta | None = None
    parameters: Path | None = None


@dataclass
class SuiteDefinition:
    name: str
    setup: list[Path]
    tests: list[SuiteTestEntry]
    between_tests: list[Path]
    teardown: list[Path]
    fail_fast: bool = False
    cycle_count: int = 1
    cycle_for: timedelta | None = None


@dataclass(frozen=True)
class _ScriptRunner:
    run: Callable[[Path], None]
    error_type: type[BaseException]


class SuiteError(RuntimeError):
    pass


def parse_repeat_duration(value: str, *, field: str = "repeat_for") -> timedelta:
    text = value.strip()
    if not text:
        raise SuiteError(f"{field} duration must not be empty")
    match = _DURATION_RE.fullmatch(text)
    if not match or not any(match.group(n) for n in ("days", "hours", "minutes", "seconds")):
        raise SuiteError(
            f"Invalid {field} duration {value!r}; use suffixes s, m, h, d (e.g. 30s, 24h)",
        )
    return timedelta(
        days=int(match.group("days") or 0),
        hours=int(match.group("hours") or 0),
        minutes=int(match.group("minutes") or 0),
        seconds=int(match.group("seconds") or 0),
    )


def _as_path_list(value: object, field: str, base_dir: Path) -> list[Path]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SuiteError(f"Suite field `{field}` must be a list of paths")
    paths: list[Path] = []
    for item in value:
        if not isinstance(item, str):
            raise SuiteError(f"Suite field `{field}` entries must be strings")
        paths.append((base_dir / item).resolve())
    return paths


def _parse_parameters_field(item: dict[str, object], base_dir: Path, *, index: int) -> Path | None:
    raw = item.get("parameters")
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise SuiteError(f"Suite tests[{index}] parameters must be a non-empty string path")
    return (base_dir / raw).resolve()


def _parse_test_entry(item: object, base_dir: Path, *, index: int) -> SuiteTestEntry:
    if isinstance(item, str):
        return SuiteTestEntry(path=(base_dir / item).resolve())
    if not isinstance(item, dict):
        raise SuiteError(f"Suite tests[{index}] must be a path string or inline table")
    path = item.get("path")
    if not path or not isinstance(path, str):
        raise SuiteError(f"Suite tests[{index}] table requires string field `path`")
    resolved = (base_dir / path).resolve()
    parameters = _parse_parameters_field(item, base_dir, index=index)
    repeat_count = item.get("repeat_count")
    repeat_for = item.get("repeat_for")
    if repeat_count is not None and repeat_for is not None:
        raise SuiteError(f"Suite tests[{index}] cannot set both repeat_count and repeat_for")
    if repeat_count is not None:
        if not isinstance(repeat_count, int) or isinstance(repeat_count, bool):
            raise SuiteError(f"Suite tests[{index}] repeat_count must be an integer")
        if repeat_count < 1:
            raise SuiteError(f"Suite tests[{index}] repeat_count must be >= 1")
        return SuiteTestEntry(path=resolved, repeat_count=repeat_count, parameters=parameters)
    if repeat_for is not None:
        if not isinstance(repeat_for, str):
            raise SuiteError(f"Suite tests[{index}] repeat_for must be a string")
        return SuiteTestEntry(
            path=resolved,
            repeat_for=parse_repeat_duration(repeat_for),
            parameters=parameters,
        )
    return SuiteTestEntry(path=resolved, parameters=parameters)


def _parse_tests(value: object, base_dir: Path) -> list[SuiteTestEntry]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SuiteError("Suite field `tests` must be a list")
    return [_parse_test_entry(item, base_dir, index=index) for index, item in enumerate(value)]


def _parse_cycle(raw: dict[str, Any]) -> tuple[int, timedelta | None]:
    cycle_count = raw.get("cycle_count")
    cycle_for = raw.get("cycle_for")
    if cycle_count is not None and cycle_for is not None:
        raise SuiteError("Suite cannot set both cycle_count and cycle_for")
    if cycle_count is not None:
        if not isinstance(cycle_count, int) or isinstance(cycle_count, bool):
            raise SuiteError("Suite field `cycle_count` must be an integer")
        if cycle_count < 1:
            raise SuiteError("Suite field `cycle_count` must be >= 1")
        return cycle_count, None
    if cycle_for is not None:
        if not isinstance(cycle_for, str):
            raise SuiteError("Suite field `cycle_for` must be a string")
        return 1, parse_repeat_duration(cycle_for, field="cycle_for")
    return 1, None


def _as_bool(value: object, field: str) -> bool:
    if value is None:
        return False
    parsed = coerce_config_bool(value)
    if parsed is None:
        raise SuiteError(f"Suite field `{field}` must be a boolean")
    return parsed


def load_suite_toml(path: Path) -> SuiteDefinition:
    suite_path = path.resolve()
    if not suite_path.exists():
        raise SuiteError(f"Suite file not found: {suite_path}")
    try:
        raw = read_relaxed_toml(suite_path)
    except UnicodeDecodeError as exc:
        raise SuiteError(f"Suite file is not valid UTF-8: {suite_path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise SuiteError(f"Invalid suite TOML: {exc}") from exc

    if "rip_cord" in raw:
        raise SuiteError(
            "Suite field `rip_cord` was removed; use `fail_fast = true` instead "
            "(abort remaining setup/between/test work after any of those slots fail, "
            "always run teardown, and fail the suite)",
        )

    name = raw.get("name")
    if not name or not isinstance(name, str):
        raise SuiteError("Suite TOML requires string field `name`")
    base = suite_path.parent
    tests = _parse_tests(raw.get("tests"), base)
    if not tests:
        raise SuiteError("Suite TOML requires non-empty `tests` list")
    for entry in tests:
        if not entry.path.exists():
            raise SuiteError(f"Test script not found: {entry.path}")
    setup = _as_path_list(raw.get("setup"), "setup", base)
    between_tests = _as_path_list(raw.get("between_tests"), "between_tests", base)
    teardown = _as_path_list(raw.get("teardown"), "teardown", base)
    for script_path in setup + between_tests + teardown:
        if not script_path.exists():
            raise SuiteError(f"Suite script not found: {script_path}")
    cycle_count, cycle_for = _parse_cycle(raw)
    return SuiteDefinition(
        name=name,
        setup=setup,
        tests=tests,
        between_tests=between_tests,
        teardown=teardown,
        fail_fast=_as_bool(raw.get("fail_fast"), "fail_fast"),
        cycle_count=cycle_count,
        cycle_for=cycle_for,
    )


def _stop_remaining_work(ctx: RuntimeContext, test_path: Path, reason: str) -> None:
    """Record fail-fast stop on the session (durable), then best-effort slot DB."""
    ctx.session.mark_fail_fast_stopped(test_path, reason)
    if ctx.db.is_initialized():
        ctx.db.insert_run_metadata("fail_fast_stopped", "1")
        ctx.db.insert_event("INFO", "runner", f"fail_fast_stop:{test_path}:{reason}")
    if ctx.logger is not None:
        ctx.logger.error("fail_fast: stopping remaining tests after %s (%s)", test_path, reason)


def _suite_is_cycling(suite: SuiteDefinition) -> bool:
    return suite.cycle_count > 1 or suite.cycle_for is not None


def _cycle_exhausted(
    suite: SuiteDefinition, cycle_index: int, deadline: float | None,
) -> bool:
    if cycle_index == 0:
        return False
    if suite.cycle_for is not None:
        return deadline is not None and time.monotonic() >= deadline
    return cycle_index >= suite.cycle_count


def _repeat_exhausted(
    entry: SuiteTestEntry, repeat_index: int, deadline: float | None,
) -> bool:
    if repeat_index == 0:
        return False
    if entry.repeat_for is not None:
        return deadline is not None and time.monotonic() >= deadline
    return repeat_index >= entry.repeat_count


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
    begin_script_slot(ctx, script.stem, phase=phase, affects_suite_result=affects_suite_result)
    ctx.slot_script_path = script
    ctx.slot_test_index = test_index
    ctx.slot_repeat_index = repeat_index
    ctx.slot_cycle_index = cycle_index

    from colosseum.config.parameters import (
        ParametersError,
        attach_parameters,
        resolve_parameters_path,
    )

    entry_parameters = entry.parameters if entry is not None else None
    resolved_parameters = resolve_parameters_path(
        script_path=script if phase == "test" else None,
        cli_path=ctx.run_options.parameters_path,
        entry_path=entry_parameters if phase == "test" else None,
    )
    try:
        attach_parameters(
            ctx,
            resolved_parameters,
            required=ctx.run_options.parameters_path is not None
            or (phase == "test" and entry_parameters is not None),
        )
    except ParametersError as exc:
        ctx.result_aggregator.mark_suite_error(str(exc))
        if ctx.logger is not None:
            ctx.logger.error("Parameters load failed: %s", exc)
        if not ctx.slot_finalized:
            finalize_script_slot(
                ctx,
                script_path=script,
                test_index=test_index,
                repeat_index=repeat_index,
                cycle_index=cycle_index,
            )
        return bool(suite.fail_fast and phase != "teardown")

    if test_index is not None and repeat_index is not None and entry is not None:
        repeat_meta = {"test_index": str(test_index), "test_repeat_index": str(repeat_index)}
        if cycle_index is not None:
            repeat_meta["cycle_index"] = str(cycle_index)
        if entry.repeat_for is not None:
            repeat_meta.update(
                repeat_mode="duration",
                repeat_limit=str(int(entry.repeat_for.total_seconds())),
            )
        elif entry.repeat_count > 1:
            repeat_meta.update(repeat_mode="count", repeat_limit=str(entry.repeat_count))
        for key, value in repeat_meta.items():
            ctx.db.insert_run_metadata(key, value)
        ctx.db.insert_event(
            "INFO",
            "runner",
            f"test_repeat_start:{script}:test={test_index}:repeat={repeat_index}",
        )

    script_crash = False
    try:
        runner.run(script)
    except runner.error_type:
        script_crash = True
        ctx.result_aggregator.mark_suite_error(f"{phase} script failed")

    slot_has_failure = script_crash or not ctx.result_aggregator.overall_pass()
    stop_fail_fast = False
    if suite.fail_fast and slot_has_failure:
        reason = "script_error" if script_crash else "required_failure"
        if phase == "teardown":
            # Fail the suite but never skip remaining teardown scripts.
            ctx.session.mark_suite_failed(f"teardown_failure:{script}:{reason}")
        else:
            # setup / between / test: abort remaining non-teardown work.
            _stop_remaining_work(ctx, script, reason)
            stop_fail_fast = True
        if affects_suite_result:
            ctx.session.mark_suite_failed(f"test_failure:{script}:{reason}")

    if not ctx.slot_finalized:
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
    suite: SuiteDefinition, ctx: RuntimeContext, runner: _ScriptRunner,
) -> bool:
    cycling = _suite_is_cycling(suite)
    cycle_deadline = (
        time.monotonic() + suite.cycle_for.total_seconds()
        if suite.cycle_for is not None
        else None
    )
    cycle_index = 0
    while not _cycle_exhausted(suite, cycle_index, cycle_deadline):
        recorded_cycle = cycle_index if cycling else None
        for test_index, entry in enumerate(suite.tests):
            entry_deadline = (
                time.monotonic() + entry.repeat_for.total_seconds()
                if entry.repeat_for is not None
                else None
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
                    another_in_entry = (
                        entry_deadline is not None and time.monotonic() < entry_deadline
                    )
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


def run_suite(
    suite_path: Path,
    config_path: Path | None = None,
    metadata_path: Path | None = None,
    *,
    debug: bool = False,
    no_artifacts: bool = False,
    run_options: RunOptions | None = None,
) -> int:
    from colosseum.config import load_config
    from colosseum.config.metadata import load_metadata
    from colosseum.context import get_context, init_context
    from colosseum.results.exit_policy import finalize_suite
    from colosseum.runner.run_options import RunOptions

    from .single_test import ScriptRunError, run_script

    suite = load_suite_toml(suite_path)
    options = run_options or RunOptions()
    init_context(
        test_case_name=suite.name,
        suite_name=suite.name,
        config_path=config_path.resolve() if config_path else None,
        metadata_path=metadata_path.resolve() if metadata_path else None,
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

    from colosseum.results.reports import apply_enabled_reports

    apply_enabled_reports(ctx)
    ensure_suite_runtime_ready(ctx, suite.name)
    record_suite_provenance(
        ctx,
        suite_path=suite_path,
        setup=suite.setup,
        tests=[(entry.path, entry.parameters) for entry in suite.tests],
        between_tests=suite.between_tests,
        teardown=suite.teardown,
    )
    runner = _ScriptRunner(run_script, ScriptRunError)
    if ctx.logger is not None:
        ctx.logger.debug(
            "Suite %r: setup=%d tests=%d between=%d teardown=%d fail_fast=%s "
            "cycle_count=%d cycle_for=%s",
            suite.name,
            len(suite.setup),
            len(suite.tests),
            len(suite.between_tests),
            len(suite.teardown),
            suite.fail_fast,
            suite.cycle_count,
            suite.cycle_for,
        )

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
    finally:
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
        code = finalize_suite(ctx)

    if interrupt is not None:
        raise interrupt
    raise SystemExit(code)
