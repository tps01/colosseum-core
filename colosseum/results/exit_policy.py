from __future__ import annotations

from typing import NoReturn

from ..context import get_context
from ..output import ensure_runtime_ready


def endex() -> NoReturn:
    """Finalize the active run and exit the process.

    Flushes logs, writes ``summary.txt`` and ``summary.json``, closes the SQLite
    database and cached instrument resources, runs plugin shutdown hooks, then
    exits with ``0`` when all required verifications pass or ``1`` otherwise.

    :returns: Does not return; raises ``SystemExit`` with the aggregate exit code.
    :rtype: NoReturn

    :raises SystemExit: Exit code ``1`` when no run context exists or the run was
        already finalized; otherwise ``0`` (PASS) or ``1`` (FAIL).
    """
    ctx = get_context()
    if ctx is None:
        raise SystemExit(1)

    if ctx.finalized:
        raise SystemExit(ctx.final_exit_code if ctx.final_exit_code is not None else 1)

    ensure_runtime_ready(ctx)
    code = ctx.result_aggregator.exit_code()
    overall = "PASS" if code == 0 else "FAIL"
    if ctx.logger is not None:
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
    ctx.db.insert_run_metadata("overall_status", overall)
    ctx.db.insert_run_metadata("exit_code", str(code))
    ctx.db.flush()
    if ctx.output_dir is not None:
        from ..summary.writer import SummaryWriter

        SummaryWriter().write(ctx.output_dir, ctx.result_aggregator, ctx)
    if ctx.logger is not None:
        ctx.logger.debug("Running plugin shutdown hooks")
    ctx.plugin_registry.run_shutdown()
    resource_count = len(ctx.resource_cache)
    if ctx.logger is not None and resource_count:
        ctx.logger.debug("Closing %d cached resource(s)", resource_count)
    for resource in list(ctx.resource_cache.values()):
        close = getattr(resource, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                if ctx.logger is not None:
                    ctx.logger.exception("Failed to close resource")
    ctx.resource_cache.clear()
    if ctx.logger is not None:
        ctx.logger.info("Overall result: %s (exit %s)", overall, code)
        for handler in list(ctx.logger.handlers):
            handler.flush()
            handler.close()
        ctx.logger.handlers.clear()
    ctx.db.close()
    ctx.finalized = True
    ctx.final_exit_code = code
    ctx._finalized_count += 1
    raise SystemExit(code)
