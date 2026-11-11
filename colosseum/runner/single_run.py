"""Single-run orchestration for ``colosseum run``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from colosseum.config import load_config
from colosseum.context import RuntimeContext, init_context
from colosseum.database.evidence_import import import_evidence_from_previous
from colosseum.paths import absolute_path
from colosseum.results.exit_policy import endex
from colosseum.runner.provenance import record_single_provenance
from colosseum.runner.run_options import RunOptions
from colosseum.runner.runtime import ensure_runtime_ready

from .single_test import ScriptRunError, run_script

if TYPE_CHECKING:
    from pathlib import Path


def _load_run_config(config_path: str | None, metadata_path: str | None = None) -> None:
    from colosseum.context import get_context

    if config_path:
        load_config(config_path, metadata_path=metadata_path)
    elif metadata_path:
        from colosseum.config.metadata import load_metadata

        load_metadata(metadata_path)
    ctx = get_context()
    if config_path:
        ctx.session.config_pinned = True
    if metadata_path:
        ctx.session.metadata_pinned = True


def _import_previous_evidence(ctx: object, run_options: RunOptions) -> None:
    if run_options.execution_mode != "verify_only":
        return
    if run_options.previous_output_dir is None:
        raise RuntimeError("verify_only mode requires --use-previous-output")
    import_evidence_from_previous(ctx, run_options.previous_output_dir)


def _prepare_single_parameters(
    ctx: RuntimeContext,
    options: RunOptions,
    test_path: Path,
    resolved_parameters: Path | None,
) -> bool:
    """Attach parameters. Returns False when the run should stop."""
    from colosseum.config.parameters import ParametersError, attach_parameters

    try:
        attach_parameters(
            ctx,
            resolved_parameters,
            required=options.parameters_path is not None,
        )
    except ParametersError as exc:
        record_single_provenance(ctx, test_path, resolved_parameters)
        ctx.result_aggregator.mark_suite_error(str(exc))
        if ctx.logger is not None:
            ctx.logger.error("Parameters load failed: %s", exc)
        endex()
        return False
    return True


def _execute_single_test_body(ctx: RuntimeContext, test_path: Path) -> None:
    """Run the test script and record suite errors on failure."""
    try:
        run_script(test_path)
    except ScriptRunError:
        ctx.result_aggregator.mark_suite_error("test script failed")
    except Exception as exc:
        ctx.result_aggregator.mark_suite_error(f"test run failed: {exc}")
        if ctx.logger is not None:
            ctx.logger.exception("Unhandled error during test run")


def _run_single_test(
    test_path: Path,
    config_path: str | None,
    metadata_path: str | None,
    *,
    debug: bool = False,
    no_artifacts: bool = False,
    run_options: RunOptions | None = None,
) -> None:
    options = run_options or RunOptions()
    ctx = init_context(
        test_case_name=test_path.stem,
        config_path=absolute_path(config_path) if config_path else None,
        metadata_path=absolute_path(metadata_path) if metadata_path else None,
        no_artifacts=no_artifacts,
        run_options=options,
    )
    ctx.debug_logging = debug
    ctx.active_execution_mode = options.execution_mode
    _load_run_config(config_path, metadata_path)
    ensure_runtime_ready(ctx)
    from colosseum.config.parameters import resolve_parameters_path
    from colosseum.results.reports import apply_enabled_reports

    apply_enabled_reports(ctx)
    resolved_parameters = resolve_parameters_path(
        script_path=test_path,
        cli_path=options.parameters_path,
    )
    if not _prepare_single_parameters(ctx, options, test_path, resolved_parameters):
        return
    record_single_provenance(ctx, test_path, resolved_parameters)
    _import_previous_evidence(ctx, options)
    try:
        _execute_single_test_body(ctx, test_path)
    finally:
        endex()
