"""Same-interpreter complete runs must execute, terminate, and release resources."""

from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path

import pytest

from colosseum.context import get_context
from colosseum.logging.setup import _detach_handlers
from colosseum.runner.cli import run_cli

_SCRIPT = '''
import os
from pathlib import Path

def main() -> None:
    from colosseum.context import get_context
    from colosseum.database import MeasurementRow

    ctx = get_context()
    marker = Path(os.environ["COMPLETE_RUN_MARKER"])
    mode = os.environ["COMPLETE_RUN_MODE"]

    def sample() -> None:
        ctx.db.enqueue_measurement(
            MeasurementRow(domain="core", command="listener", key="v", value=1),
        )

    class Resource:
        def close(self) -> None:
            sample()

    ctx.resource_cache["probe"] = Resource()

    def shutdown() -> None:
        ctx.db.insert_event("INFO", "probe", "shutdown")
        marker.write_text(marker.read_text(encoding="utf-8") + "shutdown\\n", encoding="utf-8")

    ctx.plugin_registry.register_shutdown(shutdown)
    if mode == "storage_error":
        def fail_commit() -> None:
            raise OSError("injected commit failure")

        ctx.db._write_queue._commit = fail_commit  # noqa: SLF001
    sample()
    ctx.db.insert_event("INFO", "probe", "executed")
    marker.write_text("executed\\n", encoding="utf-8")
    if mode == "script_error":
        raise RuntimeError("injected script failure")
'''


def _writer_ids() -> set[int]:
    return {
        ident
        for thread in threading.enumerate()
        if thread.name == "colosseum-db-writer" and (ident := thread.ident) is not None
    }


def _release(ctx) -> None:
    if isinstance(ctx.logger, logging.Logger):
        _detach_handlers(ctx.logger)
        ctx.logger = None
    if ctx.db.is_initialized():
        ctx.db.close()


@pytest.mark.parametrize("no_artifacts", [False, True])
@pytest.mark.parametrize("mode", ["normal", "script_error", "storage_error"])
def test_complete_run_executes_and_releases(
    mode: str,
    no_artifacts: bool,
    core_config: Path,
    isolated_cwd: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = isolated_cwd / "complete_run.py"
    script.write_text(_SCRIPT, encoding="utf-8")
    marker = isolated_cwd / "complete_run_marker.txt"
    monkeypatch.setenv("COMPLETE_RUN_MODE", mode)
    monkeypatch.setenv("COMPLETE_RUN_MARKER", str(marker))
    baseline_writers = _writer_ids()
    baseline_handlers = len(logging.getLogger("colosseum").handlers)
    seen: list[object] = []
    seen_dirs: list[Path] = []

    for _iteration in range(2):
        marker.write_text("", encoding="utf-8")
        argv = ["run", str(script), "--config", str(core_config)]
        if no_artifacts:
            argv.append("--no-artifacts")
        outcome = "returned"
        try:
            code = run_cli(argv)
            outcome = f"returned {code}"
        except SystemExit as exc:
            outcome = f"exit {0 if exc.code is None else exc.code}"
        except OSError as exc:
            outcome = f"oserror {exc}"
        finally:
            try:
                ctx = get_context()
            except RuntimeError as exc:
                pytest.fail(f"run did not leave a context ({outcome}): {exc}")
            try:
                _assert_completed_run(
                    ctx,
                    mode=mode,
                    no_artifacts=no_artifacts,
                    outcome=outcome,
                    marker=marker,
                    seen=seen,
                    seen_dirs=seen_dirs,
                    baseline_writers=baseline_writers,
                    baseline_handlers=baseline_handlers,
                    cwd=isolated_cwd,
                )
            finally:
                _release(ctx)


def _assert_completed_run(
    ctx,
    *,
    mode: str,
    no_artifacts: bool,
    outcome: str,
    marker: Path,
    seen: list[object],
    seen_dirs: list[Path],
    baseline_writers: set[int],
    baseline_handlers: int,
    cwd: Path,
) -> None:
    if mode == "normal":
        assert outcome == "exit 0"
    elif mode == "script_error":
        assert outcome == "exit 1"
    else:
        assert "injected commit failure" in outcome
    assert marker.read_text(encoding="utf-8") == "executed\nshutdown\n"
    assert ctx.test_case_name == "complete_run"
    assert all(ctx is not previous for previous in seen)
    seen.append(ctx)
    assert not ctx.db.is_initialized()
    assert not ctx.resource_cache
    assert _writer_ids() <= baseline_writers
    assert len(logging.getLogger("colosseum").handlers) == baseline_handlers
    if no_artifacts:
        assert ctx.output_dir is None
        assert not (cwd / "outputs").exists()
        return
    assert ctx.output_dir is not None
    assert ctx.output_dir not in seen_dirs
    seen_dirs.append(ctx.output_dir)
    database = ctx.output_dir / "execution.sqlite"
    assert database.is_file()
    with sqlite3.connect(database) as connection:
        if mode == "storage_error":
            assert connection.execute("SELECT COUNT(*) FROM run_result").fetchone()[0] == 0
        else:
            assert connection.execute("SELECT COUNT(*) FROM measurements").fetchone()[0] == 2
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM events WHERE message='shutdown'",
                ).fetchone()[0]
                == 1
            )
