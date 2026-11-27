from __future__ import annotations

import atexit
import sys
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from colosseum.context import RuntimeContext, get_context
from colosseum.logging.setup import close_logger_handlers
from colosseum.runner.runtime import rename_run_directory_for_result
from colosseum.runner.session import INTERRUPTION_REASON

from .finalize import close_resource_cache, finalize_run
from .finalize_policy import policy_for_single

if TYPE_CHECKING:
    from types import TracebackType

    from colosseum.summary.writer import SuiteSummaryWriter

_ORIGINAL_EXCEPTHOOK = sys.excepthook
_AUTO_FINALIZE_HOOKS_REGISTERED = False


def _finalize_context(ctx: RuntimeContext) -> int:
    try:
        result = finalize_run(ctx, policy=policy_for_single(run_shutdown=True))
    except BaseException:
        # Do not replay shutdown or turn a failed completion into PASS on retry.
        ctx.finalized = True
        ctx.final_exit_code = 1
        raise
    ctx.finalized = True
    ctx.final_exit_code = result.exit_code
    return result.exit_code


def _log_suite_result(
    ctx: RuntimeContext,
    summary: dict[str, Any],
    *,
    overall: str,
    code: int,
) -> None:
    if ctx.logger is None:
        return
    with suppress(Exception):
        ctx.logger.info("Suite overall result: %s (exit %s)", overall, code)
        if ctx.session.interrupted:
            ctx.logger.info(INTERRUPTION_REASON)
    with suppress(Exception):
        from colosseum.summary.requirements import (
            requirement_lines,
        )

        for line in requirement_lines(
            summary["requirements"],
            suite=True,
        ):
            if line:
                ctx.logger.info(line)


def _shutdown_suite_resources(ctx: RuntimeContext) -> None:
    def mark_interrupted() -> None:
        if ctx.session.interrupted:
            raise KeyboardInterrupt
        ctx.session.interrupted = True

    try:
        with suppress(Exception):
            ctx.plugin_registry.run_shutdown()
    except KeyboardInterrupt:
        mark_interrupted()
    finally:
        with suppress(Exception):
            close_resource_cache(ctx.resource_cache, logger=ctx.logger, on_interrupt=mark_interrupted)


def _close_suite_logger(ctx: RuntimeContext) -> None:
    if ctx.logger is not None:
        try:
            close_logger_handlers(ctx.logger)
        except Exception as exc:  # noqa: BLE001 - still rename and write summary
            print(f"Colosseum: failed to close suite logger: {exc}", file=sys.stderr)
        ctx.logger = None


def _persist_suite_artifacts(
    ctx: RuntimeContext,
    writer: SuiteSummaryWriter,
    summary: dict[str, Any],
    *,
    overall: str,
    code: int,
) -> None:
    from colosseum.runner.runtime import refresh_slot_artifacts

    if ctx.suite_output_dir is None or ctx.no_artifacts:
        return

    original_root = ctx.suite_output_dir
    # Rename is resilient; write afterward so summary paths match the final dir.
    try:
        ctx.suite_output_dir = rename_run_directory_for_result(
            ctx.suite_output_dir,
            overall,
        )
    except Exception as exc:  # noqa: BLE001 - keep original path for summary
        print(
            f"Colosseum: failed to rename suite container: {exc}",
            file=sys.stderr,
        )
    try:
        if ctx.suite_output_dir != original_root:
            for slot in ctx.suite_slot_results:
                slot.output_dir = ctx.suite_output_dir / slot.output_dir.relative_to(
                    original_root,
                )
                refresh_slot_artifacts(ctx, slot)
        summary["test_slots"] = [slot.as_dict() for slot in ctx.suite_test_results]
        summary["all_slots"] = [slot.as_dict() for slot in ctx.suite_slot_results]
        writer.write(
            ctx.suite_output_dir,
            ctx,
            exit_code=code,
            overall=overall,
            payload=summary,
        )
        if reason := summary.get("interruption_reason"):
            from colosseum.summary.junit import write_suite_interruption

            write_suite_interruption(ctx.suite_output_dir, ctx, reason)
    except Exception as exc:  # noqa: BLE001 - suite exit code still returned
        print(
            f"Colosseum: failed to write suite artifacts: {exc}",
            file=sys.stderr,
        )


def finalize_suite(ctx: RuntimeContext) -> int:
    """Finalize a suite container after all script slots have completed.

    Each side effect is isolated so a logger-close or summary-write failure still
    returns the suite exit code. A first interrupt during cleanup marks the
    suite incomplete.
    """
    from colosseum.results.aggregation import build_suite_summary
    from colosseum.summary.writer import SuiteSummaryWriter

    writer = SuiteSummaryWriter()
    try:
        _shutdown_suite_resources(ctx)
    except KeyboardInterrupt:
        _close_suite_logger(ctx)
        raise
    ctx.session.interrupted |= ctx.session.cancel_requested
    code = 1 if ctx.session.interrupted else writer.suite_exit_code(ctx)
    overall = ("INCOMPLETE" if ctx.session.interrupted else "FAIL") if code else "PASS"
    summary = build_suite_summary(ctx, exit_code=code, overall=overall)

    _log_suite_result(ctx, summary, overall=overall, code=code)
    _close_suite_logger(ctx)
    _persist_suite_artifacts(ctx, writer, summary, overall=overall, code=code)

    ctx.suite_finalized = True
    ctx.finalized = True
    ctx.final_exit_code = code
    return code


def _auto_finalize_active_context() -> None:
    try:
        ctx = get_context()
    except RuntimeError:
        return
    if ctx.finalized or not ctx.auto_finalize:
        return
    try:
        _finalize_context(ctx)
    except Exception as exc:  # pragma: no cover - process-exit last resort  # noqa: BLE001
        print(f"Colosseum auto-finalization failed: {exc}", file=sys.stderr)


def _handle_unhandled_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    try:
        ctx = get_context()
    except RuntimeError:
        ctx = None
    if ctx is not None and not ctx.finalized and ctx.auto_finalize:
        if isinstance(exc_value, KeyboardInterrupt):
            ctx.interrupted = True
        else:
            ctx.result_aggregator.mark_suite_error(f"unhandled exception: {exc_value}")
            if ctx.db.is_initialized():
                with suppress(Exception):
                    ctx.db.insert_event("ERROR", "runner", f"unhandled_exception:{exc_value}")
    _ORIGINAL_EXCEPTHOOK(exc_type, exc_value, exc_traceback)


def register_auto_finalize_hooks() -> None:
    global _AUTO_FINALIZE_HOOKS_REGISTERED

    if _AUTO_FINALIZE_HOOKS_REGISTERED:
        return
    sys.excepthook = _handle_unhandled_exception
    atexit.register(_auto_finalize_active_context)
    _AUTO_FINALIZE_HOOKS_REGISTERED = True


def endex() -> None:
    """Finalize the active run.

    During a suite run, finalizes the current script slot and returns without
    exiting the process. For single-test runs, exits with the aggregate code.
    Suite vs single is determined by ``session.kind`` (not artifact paths), so
    no-artifacts suites still finalize the slot only.
    """
    try:
        ctx = get_context()
    except RuntimeError:
        raise SystemExit(1) from None

    if ctx.finalized:
        raise SystemExit(ctx.final_exit_code if ctx.final_exit_code is not None else 1)

    pending_exception = sys.exc_info()[1]
    if isinstance(pending_exception, KeyboardInterrupt) and not ctx.slot_finalized:
        ctx.interrupted = True
    if ctx.session.kind == "suite" and not ctx.suite_finalized:
        from colosseum.runner.runtime import finalize_script_slot

        if ctx.slot_finalized:
            return
        if ctx.slot_script_path is None:
            raise SystemExit(1)
        finalize_script_slot(
            ctx,
            script_path=ctx.slot_script_path,
            test_index=ctx.slot_test_index,
            repeat_index=ctx.slot_repeat_index,
            cycle_index=ctx.slot_cycle_index,
        )
        if isinstance(pending_exception, KeyboardInterrupt):
            raise pending_exception
        return

    code = _finalize_context(ctx)
    raise SystemExit(code)
