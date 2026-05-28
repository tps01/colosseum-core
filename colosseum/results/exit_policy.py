from __future__ import annotations

import sys
from typing import NoReturn

from ..context import get_context
from ..output import ensure_output_dir


def endex() -> NoReturn:
    ctx = get_context()
    if ctx is None:
        raise SystemExit(1)

    if ctx.finalized:
        raise SystemExit(ctx.final_exit_code if ctx.final_exit_code is not None else 1)

    ensure_output_dir(ctx)
    code = ctx.result_aggregator.exit_code()
    overall = "PASS" if code == 0 else "FAIL"
    ctx.db.insert_run_metadata("overall_status", overall)
    ctx.db.insert_run_metadata("exit_code", str(code))
    if ctx.output_dir is not None:
        from ..summary.writer import SummaryWriter

        SummaryWriter().write(ctx.output_dir, ctx.result_aggregator, ctx)
    if ctx.logger is not None:
        ctx.logger.info("Overall result: %s (exit %s)", overall, code)
        for handler in list(ctx.logger.handlers):
            handler.flush()
            handler.close()
        ctx.logger.handlers.clear()
    ctx.db.close()
    ctx.plugin_registry.run_shutdown()
    for resource in list(ctx.resource_cache.values()):
        close = getattr(resource, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                if ctx.logger is not None:
                    ctx.logger.exception("Failed to close resource")
    ctx.resource_cache.clear()
    ctx.finalized = True
    ctx.final_exit_code = code
    ctx._finalized_count += 1
    raise SystemExit(code)
