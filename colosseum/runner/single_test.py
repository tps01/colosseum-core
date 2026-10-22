from __future__ import annotations

import runpy
import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING

from colosseum.context import get_context

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class ScriptRunError(RuntimeError):
    pass


def _system_exit_code(exc: SystemExit) -> int:
    code = exc.code
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    return 1


@contextmanager
def _script_import_path(script: Path) -> Iterator[None]:
    """Set the active script and put its directory first on ``sys.path``.

    Matches ``python script.py``: the script directory is ``sys.path[0]`` while
    ``runpy`` loads the file and ``main()`` runs. ``sys.path`` is restored
    afterward, along with the previous active script. Sibling modules stay in
    ``sys.modules`` for the process so suite slots share helpers. Names that
    collide with an already-imported module or with stdlib/plugin names resolve
    the same way as a direct Python launch.
    """
    ctx = get_context()
    previous_script = ctx.active_script_path
    ctx.active_script_path = script
    directory = str(script.parent)
    saved = list(sys.path)
    if not sys.path or sys.path[0] != directory:
        sys.path.insert(0, directory)
    try:
        yield
    finally:
        sys.path[:] = saved
        ctx.active_script_path = previous_script


def run_script(path: Path) -> None:
    """Execute a test/setup/teardown script (calls main() only; no endex)."""
    ctx = get_context()
    resolved = path.resolve()
    ctx.db.insert_run_metadata("active_script", str(resolved))
    ctx.db.insert_event("INFO", "runner", f"script_start:{resolved}")
    if ctx.logger is not None:
        ctx.logger.info("Running script %s (phase=%s)", resolved, ctx.phase)
        ctx.logger.debug("Loading script module: %s", resolved)
    try:
        with _script_import_path(resolved):
            module_globals = runpy.run_path(str(resolved), run_name="colosseum.test_run")
            main_fn = module_globals.get("main")
            if not callable(main_fn):
                raise ScriptRunError(f"Script does not define callable main(): {resolved}")
            if ctx.logger is not None:
                ctx.logger.debug("Calling main() in %s", resolved)
            main_fn()
    except SystemExit as exc:
        if ctx.finalized:
            raise
        # Suite slot already finalized via endex() — do not treat as script crash.
        if ctx.session.kind == "suite" and ctx.slot_finalized:
            return
        code = _system_exit_code(exc)
        message = f"script_exit:{resolved}: code={code}"
        if ctx.db.is_initialized():
            ctx.db.insert_event("ERROR", "runner", message)
        if ctx.logger is not None:
            ctx.logger.error("Script exited before col.endex(): %s (code=%s)", resolved, code)
        raise ScriptRunError(message) from exc
    except Exception as exc:
        if ctx.db.is_initialized():
            ctx.db.insert_event("ERROR", "runner", f"script_fail:{resolved}: {exc}")
        if ctx.logger is not None:
            ctx.logger.exception("Script failed: %s", resolved)
        raise ScriptRunError(str(exc)) from exc
    # endex() may have already finalized (and closed) the slot database.
    if ctx.slot_finalized:
        return
    ctx.db.insert_event("INFO", "runner", f"script_done:{resolved}")
    if ctx.logger is not None:
        ctx.logger.debug("Script finished: %s", resolved)
