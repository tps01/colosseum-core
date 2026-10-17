from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from colosseum.logging.setup import close_logger_handlers
from colosseum.results.finalize_policy import (
    FinalizePolicy,
    policy_for_single,
    policy_for_suite_slot,
)
from colosseum.runner.runtime import ensure_runtime_ready, rename_run_directory_for_result

if TYPE_CHECKING:
    import logging
    from pathlib import Path

    from colosseum.context import RuntimeContext
    from colosseum.database.manager import MeasurementRecord, VerificationRecord


@dataclass
class FinalizeRunResult:
    exit_code: int
    overall: str
    measurement_count: int
    command_count: int
    verifications: list[VerificationRecord]
    measurements: list[MeasurementRecord]


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


def _write_run_artifacts(
    output_dir: Path,
    ctx: RuntimeContext,
    result: FinalizeRunResult,
) -> None:
    from colosseum.summary.wats import write_wats_report
    from colosseum.summary.writer import SummaryWriter

    SummaryWriter().write(
        output_dir,
        ctx.result_aggregator,
        ctx,
        measurement_count=result.measurement_count,
        command_count=result.command_count,
    )
    write_wats_report(
        output_dir,
        ctx,
        ctx.result_aggregator,
        result.verifications,
        result.measurements,
    )


def finalize_run(
    ctx: RuntimeContext,
    *,
    mode: Literal["single", "slot"] | None = None,
    affects_suite_result: bool = True,
    run_shutdown: bool = False,
    policy: FinalizePolicy | None = None,
) -> FinalizeRunResult:
    """Shared finalize path for single runs and suite script slots.

    Prefer ``policy=`` for new callers. ``mode`` / ``affects_suite_result`` /
    ``run_shutdown`` remain for compatibility and derive a policy when omitted.
    """
    if policy is None:
        if mode == "slot" or (mode is None and ctx.session.kind == "suite"):
            policy = policy_for_suite_slot(affects_suite_result=affects_suite_result)
        else:
            policy = policy_for_single(run_shutdown=run_shutdown)

    if policy.kind == "single":
        ensure_runtime_ready(ctx)

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
    if ctx.db.is_initialized():
        status = overall if policy.scores_suite else "N/A"
        ctx.db.insert_run_metadata("overall_status", status)
        ctx.db.insert_run_metadata("exit_code", str(code))
        measurement_count = ctx.db.count_rows("measurements")
        command_count = ctx.db.count_rows("commands")
        verifications = ctx.db.fetch_all_verifications()
        measurements = ctx.db.fetch_all_measurements()
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
    )

    if policy.rename_dir and ctx.output_dir is not None:
        ctx.output_dir = rename_run_directory_for_result(ctx.output_dir, overall)
    if policy.write_summary and ctx.output_dir is not None:
        _write_run_artifacts(ctx.output_dir, ctx, result)

    return result
