from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from colosseum.config.parameters import owed_limit_keys
from colosseum.database import VerificationRow
from colosseum.decorators.verification import VerificationResult, verification_limit_fields
from colosseum.logging.setup import close_logger_handlers
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
    for row in ctx.result_aggregator._records:  # noqa: SLF001
        if row["kind"] == "command" and not row["optional"] and row["status"] == "ERROR":
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
        expected, compare_op, tolerance = verification_limit_fields(fields)
        result = VerificationResult(status="BLOCKED", message=abort_message, optional=False)
        ctx.result_aggregator.record_verification(
            result, key=key, command="owed_limit", domain="core",
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
    )
    ctx.plugin_registry.run_listeners(ctx.enabled_reports, output_dir, result, ctx)


def finalize_run(
    ctx: RuntimeContext,
    *,
    policy: FinalizePolicy,
) -> FinalizeRunResult:
    """Shared finalize path for single runs and suite script slots."""
    if policy.kind == "single":
        ensure_runtime_ready(ctx)

    if ctx.db.is_initialized():
        _insert_blocked_owed_keys(ctx)

    code = ctx.result_aggregator.exit_code()
    overall = "PASS" if code == 0 else "FAIL"

    if policy.kind == "single" and ctx.logger is not None:
        counts = ctx.result_aggregator.counts()
        ctx.logger.debug(
            "Finalizing run: verifications=%d required=%s optional=%s "
            "suite_error=%s teardown_failed=%s",
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
        status = overall if policy.scores_suite else "N/A"
        ctx.db.insert_run_metadata("overall_status", status)
        ctx.db.insert_run_metadata("exit_code", str(code))
        measurement_count = ctx.db.count_rows("measurements")
        command_count = ctx.db.count_rows("commands")
        verifications = ctx.db.fetch_all_verifications()
        measurements = ctx.db.fetch_all_measurements()
        commands = ctx.db.fetch_all_commands()
        ctx.db.flush()

    if policy.run_shutdown:
        if ctx.logger is not None:
            ctx.logger.debug("Running plugin shutdown hooks")
        ctx.plugin_registry.run_shutdown()

    if policy.close_resources:
        close_resource_cache(ctx.resource_cache, logger=ctx.logger)

    if ctx.logger is not None:
        if policy.kind == "single" and policy.log_overall:
            ctx.logger.info("Overall result: %s (exit %s)", overall, code)
        elif policy.log_overall:
            ctx.logger.info("Slot result: %s (exit %s)", overall, code)
        close_logger_handlers(ctx.logger)

    if ctx.db.is_initialized():
        ctx.db.close()

    result = FinalizeRunResult(
        exit_code=code,
        overall=overall,
        measurement_count=measurement_count,
        command_count=command_count,
        verifications=verifications,
        measurements=measurements,
        commands=commands,
    )

    if ctx.run_options.dry_run:
        from colosseum.decorators._common import finalize_dry_run_tips

        finalize_dry_run_tips(ctx)

    # Rename is resilient (returns the original path on OSError), so summaries
    # still land even when the -pass/-fail suffix cannot be applied, and
    # summary.json records the final directory path.
    if policy.rename_dir and ctx.output_dir is not None:
        ctx.output_dir = rename_run_directory_for_result(ctx.output_dir, overall)
    if policy.write_summary and ctx.output_dir is not None:
        _write_run_artifacts(ctx.output_dir, ctx, result)

    return result
