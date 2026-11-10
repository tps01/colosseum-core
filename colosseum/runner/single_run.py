"""Single-run orchestration for ``colosseum run``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from colosseum.config import load_config
from colosseum.context import RuntimeContext, init_context
from colosseum.database.evidence_import import import_evidence_from_previous
from colosseum.paths import absolute_path
from colosseum.results.exit_policy import endex
from colosseum.runner.command_invoke import (
    CommandInvokeError,
    command_logical_name,
    invoke_plugin_commands,
)
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


def finish_parameter_export(ctx: RuntimeContext, *, failed: bool) -> int:
    """Write ``parameters.toml`` when the walk succeeded, then close the runtime.

    The run folder is left without a ``-pass`` or ``-fail`` suffix, and no scored
    summary is written.
    """
    from colosseum.config.parameters import write_parameters_file
    from colosseum.logging.setup import close_logger_handlers
    from colosseum.results.finalize import close_resource_cache

    errors = list(ctx.export_errors)
    ready = not failed and not errors and ctx.parameter_export is not None
    if ready and ctx.output_dir is None:
        errors.append("parameter export has no output directory")
        ready = False
    if ready and ctx.output_dir is not None and ctx.parameter_export is not None:
        path = ctx.output_dir / "parameters.toml"
        write_parameters_file(path, ctx.parameter_export)
        if ctx.logger is not None:
            ctx.logger.info("Wrote parameters file: %s", path)
    elif ctx.logger is not None:
        for message in errors:
            ctx.logger.error("Parameter export failed: %s", message)
        if failed and not errors:
            ctx.logger.error("Parameter export failed: script did not finish")
    close_resource_cache(ctx.resource_cache, logger=ctx.logger)
    if ctx.logger is not None:
        close_logger_handlers(ctx.logger)
    if ctx.db.is_initialized():
        ctx.db.close()
    return 0 if ready else 1


def _import_previous_evidence(ctx: object, run_options: RunOptions) -> None:
    if run_options.execution_mode != "verify_only":
        return
    if run_options.previous_output_dir is None:
        raise RuntimeError("verify_only mode requires --use-previous-output")
    import_evidence_from_previous(ctx, run_options.previous_output_dir)


def _prepare_single_parameters(
    ctx: RuntimeContext,
    options: RunOptions,
    test_path: Path | None,
    resolved_parameters: Path | None,
    *,
    exporting: bool,
) -> bool:
    """Attach parameters or arm export. Returns False when the run should stop."""
    from colosseum.config.parameters import ParametersError, attach_parameters

    if exporting:
        ctx.parameter_export = {}
        return True
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


def _execute_single_test_body(
    ctx: RuntimeContext,
    options: RunOptions,
    test_path: Path | None,
    *,
    exporting: bool,
) -> bool:
    """Run plugin commands and/or the test script. Returns export_failed."""
    export_failed = False
    try:
        if options.plugin_commands:
            invoke_plugin_commands(ctx, options.plugin_commands)
        if test_path is not None:
            run_script(test_path)
    except (ScriptRunError, CommandInvokeError):
        if exporting:
            export_failed = True
        else:
            ctx.result_aggregator.mark_suite_error("test script failed")
    except Exception as exc:
        if exporting:
            export_failed = True
            if ctx.logger is not None:
                ctx.logger.exception("Unhandled error during parameter export")
        else:
            ctx.result_aggregator.mark_suite_error(f"test run failed: {exc}")
            if ctx.logger is not None:
                ctx.logger.exception("Unhandled error during test run")
    return export_failed


def _run_single_test(
    test_path: Path | None,
    config_path: str | None,
    metadata_path: str | None,
    *,
    debug: bool = False,
    no_artifacts: bool = False,
    run_options: RunOptions | None = None,
) -> None:
    options = run_options or RunOptions()
    logical_name = (
        test_path.stem
        if test_path is not None
        else command_logical_name(
            options.plugin_commands[0],
        )
    )
    ctx = init_context(
        test_case_name=logical_name,
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
    exporting = options.export == "parameters"
    resolved_parameters = resolve_parameters_path(
        script_path=test_path,
        cli_path=options.parameters_path,
    )
    if not _prepare_single_parameters(
        ctx,
        options,
        test_path,
        resolved_parameters,
        exporting=exporting,
    ):
        return
    record_single_provenance(ctx, test_path, resolved_parameters)
    _import_previous_evidence(ctx, options)
    export_failed = False
    try:
        export_failed = _execute_single_test_body(
            ctx,
            options,
            test_path,
            exporting=exporting,
        )
    finally:
        if exporting:
            code = finish_parameter_export(ctx, failed=export_failed)
            ctx.finalized = True
            ctx.final_exit_code = code
        endex()
