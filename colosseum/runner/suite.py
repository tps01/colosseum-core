from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config.toml_relaxed import read_relaxed_toml

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


@dataclass
class SuiteDefinition:
    name: str
    setup: list[Path]
    tests: list[Path]
    teardown: list[Path]


class SuiteError(RuntimeError):
    pass


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

    name = raw.get("name")
    if not name or not isinstance(name, str):
        raise SuiteError("Suite TOML requires string field `name`")
    tests = _as_path_list(raw.get("tests"), "tests", suite_path.parent)
    if not tests:
        raise SuiteError("Suite TOML requires non-empty `tests` list")
    for test_path in tests:
        if not test_path.exists():
            raise SuiteError(f"Test script not found: {test_path}")
    setup = _as_path_list(raw.get("setup"), "setup", suite_path.parent)
    teardown = _as_path_list(raw.get("teardown"), "teardown", suite_path.parent)
    for script_path in setup + teardown:
        if not script_path.exists():
            raise SuiteError(f"Suite script not found: {script_path}")
    return SuiteDefinition(name=name, setup=setup, tests=tests, teardown=teardown)


def _set_phase(phase: str) -> None:
    from ..context import require_context

    ctx = require_context()
    ctx.phase = phase
    ctx.db.insert_run_metadata("phase", phase)
    ctx.db.insert_event("INFO", "runner", f"phase_enter:{phase}")
    if ctx.logger is not None:
        ctx.logger.info("Suite phase: %s", phase)


def run_suite(
    suite_path: Path,
    config_path: Path | None = None,
    *,
    debug: bool = False,
    use_autoconfig: bool = False,
    autoconfig_export: Path | None = None,
    autoconfig_blacklist: list[str] | None = None,
) -> int:
    from ..config import autoconfig, load_config
    from ..context import init_context, require_context
    from ..output import ensure_output_dir
    from ..results import endex
    from .single_test import ScriptRunError, run_script

    suite = load_suite_toml(suite_path)
    init_context(
        test_case_name=suite.name,
        suite_name=suite.name,
        config_path=config_path.resolve() if config_path else None,
    )
    ctx = require_context()
    ctx.debug_logging = debug
    if use_autoconfig:
        autoconfig(
            export_path=autoconfig_export,
            blacklist=autoconfig_blacklist,
        )
    elif config_path:
        load_config(config_path)

    logical = ctx.suite_name or ctx.test_case_name
    ensure_output_dir(ctx, logical_name=logical)
    ctx.db.insert_run_metadata("suite_name", suite.name)
    if ctx.logger is not None:
        ctx.logger.debug(
            "Suite %r: setup=%d test=%d teardown=%d",
            suite.name,
            len(suite.setup),
            len(suite.tests),
            len(suite.teardown),
        )

    setup_failed = False
    _set_phase("setup")
    for script in suite.setup:
        try:
            run_script(script)
        except ScriptRunError:
            setup_failed = True
            ctx.result_aggregator.mark_suite_error("setup script failed")
            if ctx.logger is not None:
                ctx.logger.debug("Setup failed; skipping test scripts")
            break

    if not setup_failed:
        _set_phase("test")
        for index, test_path in enumerate(suite.tests):
            ctx.db.insert_run_metadata("test_index", str(index))
            try:
                run_script(test_path)
            except ScriptRunError:
                ctx.result_aggregator.mark_suite_error("test script failed")
                if ctx.logger is not None:
                    ctx.logger.error("Test script failed (continuing suite): %s", test_path)

    _set_phase("teardown")
    for script in suite.teardown:
        try:
            run_script(script)
        except ScriptRunError:
            ctx.result_aggregator.mark_teardown_failed()

    endex()
    return 0
