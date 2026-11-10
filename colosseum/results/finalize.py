from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from colosseum.config.parameters import owed_limit_keys
from colosseum.database import DatabaseManager, VerificationRow
from colosseum.decorators.verification import VerificationResult, verification_limit_fields
from colosseum.logging.setup import close_logger_handlers
from colosseum.results.aggregation import build_run_summary, coerce_requirements
from colosseum.runner.runtime import ensure_runtime_ready, rename_run_directory_for_result

if TYPE_CHECKING:
    import logging
    from pathlib import Path

    from colosseum.context import RuntimeContext
    from colosseum.database.manager import CommandRecord, MeasurementRecord, VerificationRecord
    from colosseum.results.finalize_policy import FinalizePolicy


@dataclass
class FinalizeRunResult:
    exit_code: int
    overall: str
    measurement_count: int
    command_count: int
    verifications: list[VerificationRecord]
    measurements: list[MeasurementRecord]
    commands: list[CommandRecord] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def close_resource_cache(
    cache: dict[str, object],
    *,
    logger: logging.Logger | None = None,
) -> None:
    if not cache:
        return
    if logger is not None:
        logger.debug("Closing %d cached resource(s)", len(cache))
    for key in list(cache):
        resource = cache.pop(key, None)
        close = getattr(resource, "close", None)
        if not callable(close):
            continue
        try:
            close()
        except Exception:  # noqa: BLE001
            if logger is not None:
                logger.exception("Failed to close cached resource %s", key)


def _abort_message(ctx: RuntimeContext) -> str:
    for row in ctx.result_aggregator.required_command_errors():
        domain = row.get("domain", "")
        command = row.get("command", "")
        message = row.get("message", "")
        label = f"{domain}.{command}" if domain else command
        if message:
            return f"not measured: {label}: {message}"
        return f"not measured: {label}"
    return "owed key never called"


def _insert_blocked_owed_keys(ctx: RuntimeContext) -> None:
    """Insert BLOCKED verification rows for owed limit keys with no measurement."""
    if ctx.parameters_map is None or not ctx.db.is_initialized():
        return
    measured = ctx.db.measurement_keys()
    if ctx.run_options.dry_run:
        measured.update(item[2] for item in ctx.dry_run_measurements)
    abort_message = _abort_message(ctx)
    for key in owed_limit_keys(ctx.parameters_map):
        if key in measured:
            continue
        fields = ctx.parameters_map[key]
        try:
            requirements = coerce_requirements(fields.get("requirements"))
        except TypeError:
            # Invalid attachments must not prevent the owed check being recorded.
            requirements = []
        expected, compare_op, tolerance = verification_limit_fields(fields)
        result = VerificationResult(status="BLOCKED", message=abort_message, optional=False)
        ctx.result_aggregator.record_verification(
            result,
            key=key,
            command="owed_limit",
            domain="core",
            requirements=requirements,
        )
        ctx.db.insert_verification(
            VerificationRow(
                domain="core",
                command="owed_limit",
                key=key,
                expected=expected,
                actual=None,
                tolerance=tolerance,
                compare_op=compare_op,
                status="BLOCKED",
                optional=False,
                message=abort_message,
                requirements=requirements,
            ),
        )


def _write_run_artifacts(
    output_dir: Path,
    ctx: RuntimeContext,
    result: FinalizeRunResult,
) -> None:
    from colosseum.summary.writer import SummaryWriter

    SummaryWriter().write(
        output_dir,
        ctx.result_aggregator,
        ctx,
        measurement_count=result.measurement_count,
        command_count=result.command_count,
        payload=result.summary,
    )
    ctx.plugin_registry.run_listeners(ctx.enabled_reports, output_dir, result, ctx)


def _finalize_shutdown_and_drain(ctx: RuntimeContext, policy: FinalizePolicy) -> None:
    # Existing producers finish before the evidence barrier and owed-key check.
    # Suite shutdown remains owned by the suite, never by an individual slot.
    if policy.run_shutdown:
        if ctx.logger is not None:
            ctx.logger.debug("Running plugin shutdown hooks")
        ctx.plugin_registry.run_shutdown()
    if policy.close_resources:
        close_resource_cache(ctx.resource_cache, logger=ctx.logger)

    if ctx.db.is_initialized():
        ctx.db.drain()
        _insert_blocked_owed_keys(ctx)


@dataclass
class _CollectedFinalize:
    code: int
    overall: str
    measurement_count: int
    command_count: int
    verifications: list[VerificationRecord]
    measurements: list[MeasurementRecord]
    commands: list[CommandRecord]
    summary: dict[str, Any]


def _finalize_collect(ctx: RuntimeContext, policy: FinalizePolicy) -> _CollectedFinalize:
    code = ctx.result_aggregator.exit_code()
    overall = "PASS" if code == 0 else "FAIL"

    if policy.kind == "single" and ctx.logger is not None:
        counts = ctx.result_aggregator.counts()
        ctx.logger.debug(
            "Finalizing run: verifications=%d required=%s optional=%s suite_error=%s teardown_failed=%s",
            counts["total"],
            counts["required"],
            counts["optional"],
            ctx.result_aggregator.suite_error,
            ctx.result_aggregator.teardown_failed,
        )

    measurement_count = 0
    command_count = 0
    verifications: list[VerificationRecord] = []
    measurements: list[MeasurementRecord] = []
    commands: list[CommandRecord] = []
    if ctx.db.is_initialized():
        measurement_count = ctx.db.count_rows("measurements")
        command_count = ctx.db.count_rows("commands")
        verifications = ctx.db.fetch_all_verifications()
        measurements = ctx.db.fetch_all_measurements()
        commands = ctx.db.fetch_all_commands()
        ctx.db.flush()

    if ctx.run_options.dry_run:
        from colosseum.decorators._common import finalize_dry_run_tips

        finalize_dry_run_tips(ctx)
    summary = build_run_summary(
        ctx,
        ctx.result_aggregator,
        measurement_count=measurement_count,
        command_count=command_count,
    )
    return _CollectedFinalize(
        code=code,
        overall=overall,
        measurement_count=measurement_count,
        command_count=command_count,
        verifications=verifications,
        measurements=measurements,
        commands=commands,
        summary=summary,
    )


def _finalize_log_and_close(
    ctx: RuntimeContext,
    policy: FinalizePolicy,
    collected: _CollectedFinalize,
) -> None:
    if ctx.logger is not None:
        if policy.kind == "single" and policy.log_overall:
            ctx.logger.info(
                "Overall result: %s (exit %s)",
                collected.overall,
                collected.code,
            )
        elif policy.log_overall:
            ctx.logger.info(
                "Slot result: %s (exit %s)",
                collected.overall,
                collected.code,
            )
        if policy.write_summary:
            from colosseum.summary.requirements import (
                requirement_lines,
            )

            for line in requirement_lines(
                collected.summary["requirements"],
            ):
                if line:
                    ctx.logger.info(line)
        close_logger_handlers(ctx.logger)

    if ctx.db.is_initialized():
        ctx.db.close()


def _finalize_persist_and_artifacts(
    ctx: RuntimeContext,
    policy: FinalizePolicy,
    result: FinalizeRunResult,
) -> None:
    # Rename is resilient (returns the original path on OSError), so summaries
    # still land even when the -pass/-fail suffix cannot be applied, and
    # summary.json records the final directory path.
    if policy.rename_dir and ctx.output_dir is not None:
        ctx.output_dir = rename_run_directory_for_result(ctx.output_dir, result.overall)
    result.summary["output_directory"] = str(ctx.output_dir) if ctx.output_dir is not None else None
    if ctx.output_dir is not None and (ctx.output_dir / "execution.sqlite").is_file():
        stored = {
            **result.summary,
            "stored_status": result.overall if policy.scores_suite else "N/A",
        }
        DatabaseManager.persist_results(
            ctx.output_dir / "execution.sqlite",
            stored,
            kind="slot" if policy.kind != "single" else "single",
        )
    if policy.write_summary and ctx.output_dir is not None:
        _write_run_artifacts(ctx.output_dir, ctx, result)


def finalize_run(
    ctx: RuntimeContext,
    *,
    policy: FinalizePolicy,
) -> FinalizeRunResult:
    """Shared finalize path for single runs and suite script slots."""
    try:
        if policy.kind == "single":
            ensure_runtime_ready(ctx)

        _finalize_shutdown_and_drain(ctx, policy)
        collected = _finalize_collect(ctx, policy)
        _finalize_log_and_close(ctx, policy, collected)

        result = FinalizeRunResult(
            exit_code=collected.code,
            overall=collected.overall,
            measurement_count=collected.measurement_count,
            command_count=collected.command_count,
            verifications=collected.verifications,
            measurements=collected.measurements,
            commands=collected.commands,
            summary=collected.summary,
        )
        _finalize_persist_and_artifacts(ctx, policy, result)
        return result
    except BaseException:
        # Failure must release core-owned handles without replacing the primary error.
        # A timed-out writer retains its connection so a later close can finish safely.
        if ctx.logger is not None:
            with suppress(Exception):
                close_logger_handlers(ctx.logger)
        with suppress(Exception):
            ctx.db.close()
        raise
