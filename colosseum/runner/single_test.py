from __future__ import annotations

from pathlib import Path
import runpy

from ..context import require_context


class ScriptRunError(RuntimeError):
    pass


def run_script(path: Path) -> None:
    """Execute a test/setup/teardown script (calls main() only; no endex)."""
    ctx = require_context()
    resolved = path.resolve()
    ctx.db.insert_run_metadata("active_script", str(resolved))
    ctx.db.insert_event("INFO", "runner", f"script_start:{resolved}")
    if ctx.logger is not None:
        ctx.logger.info("Running script %s (phase=%s)", resolved, ctx.phase)
    try:
        module_globals = runpy.run_path(str(resolved), run_name="colosseum.test_run")
        main_fn = module_globals.get("main")
        if callable(main_fn):
            main_fn()
    except Exception as exc:
        ctx.db.insert_event("ERROR", "runner", f"script_fail:{resolved}: {exc}")
        if ctx.logger is not None:
            ctx.logger.exception("Script failed: %s", resolved)
        raise ScriptRunError(str(exc)) from exc
    ctx.db.insert_event("INFO", "runner", f"script_done:{resolved}")
