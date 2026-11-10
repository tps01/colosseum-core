"""Cross-check persisted evidence, result facts, and disk summaries at shutdown."""

from __future__ import annotations

import io
import json
import sqlite3
import sys
import tempfile
from contextlib import ExitStack, closing, redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tests.fuzz.results import new_context


def read_result(directory: Path) -> dict:
    """Read persistence independently and check its internal outcome projections."""
    with closing(sqlite3.connect(directory / "execution.sqlite")) as reader:
        stored = reader.execute(
            "SELECT overall_result, exit_code, payload_json FROM run_result",
        ).fetchone()
        assert stored is not None, "Finalization did not persist a result"
        overall, code, encoded = stored
        metadata = dict(reader.execute("SELECT key, value FROM run_metadata"))
    payload = json.loads(encoded)
    assert (overall, code) == (payload["overall_result"], payload["exit_code"])
    assert metadata["exit_code"] == str(code)
    assert metadata["overall_status"] == payload.get("stored_status", overall)
    assert payload["output_directory"] == str(directory)
    return payload


def check_input(data: bytes) -> None:
    import colosseum.context as context_module
    import colosseum.results.finalize as finalizer
    from colosseum.database import CommandRow, MeasurementRow, VerificationRow
    from colosseum.results.exit_policy import endex
    from colosseum.runner.runtime import rename_run_directory_for_result
    from colosseum.summary.writer import SummaryWriter

    flags = data[0] if data else 0
    status = "FAIL" if flags & 1 else "PASS"
    optional = bool(flags & 2)
    code = int(status == "FAIL" and not optional)
    rename_error, report_error = bool(flags & 4), bool(flags & 8)
    count = 1 + (len(data) % 4)
    shutdown = []
    ctx = new_context()
    with tempfile.TemporaryDirectory(prefix="colosseum-disk-fuzz-") as temporary:
        original = Path(temporary) / "run"
        original.mkdir()
        ctx.output_dir, ctx.no_artifacts = original, False
        ctx.db.initialize(original / "execution.sqlite")
        for index in range(count):
            ctx.db.enqueue_measurement(
                MeasurementRow(
                    domain="core",
                    command="sample",
                    key="value",
                    row_index=index,
                    value={"index": index, "text": data[1:33].decode("utf-8", errors="replace")},
                ),
            )
        result = SimpleNamespace(status=status, optional=optional, message="fuzz")
        ctx.result_aggregator.record_verification(result, key="limit")
        ctx.db.insert_verification(
            VerificationRow(
                domain="core",
                command="limit",
                key="limit",
                status=status,
                optional=optional,
            ),
        )
        ctx.db.insert_command(CommandRow(domain="core", command="prepare"))

        def hook() -> None:
            shutdown.append(1)
            ctx.db.enqueue_measurement(
                MeasurementRow(
                    domain="core",
                    command="shutdown",
                    key="last",
                    value="settled",
                ),
            )

        def rename(directory: Path, overall: str) -> Path:
            return rename_run_directory_for_result(directory, overall, retries=1, initial_delay_s=0)

        ctx.plugin_registry.register_shutdown(hook)
        try:
            with ExitStack() as stack:
                stack.enter_context(patch.object(context_module, "_ACTIVE_CONTEXT", ctx))
                stack.enter_context(
                    patch.object(finalizer, "rename_run_directory_for_result", rename),
                )
                diagnostics = stack.enter_context(redirect_stderr(io.StringIO()))
                if rename_error:
                    stack.enter_context(
                        patch.object(Path, "rename", side_effect=OSError("rename fault")),
                    )
                if report_error:
                    stack.enter_context(
                        patch.object(SummaryWriter, "write", side_effect=OSError("report fault")),
                    )
                try:
                    endex()
                except SystemExit as exc:
                    assert not report_error and exc.code == code
                except OSError as exc:
                    assert report_error and str(exc) == "report fault"
                else:
                    raise AssertionError("endex returned")
                assert ctx.finalized and ctx.final_exit_code == (1 if report_error else code)
                for _ in range(2):
                    try:
                        endex()
                    except SystemExit as exc:
                        assert exc.code == ctx.final_exit_code
                    else:
                        raise AssertionError("Repeated endex returned")
                assert shutdown == [1] and not ctx.db.is_initialized()
                assert ctx.output_dir == (
                    original
                    if rename_error
                    else original.with_name(
                        "run-fail" if code else "run-pass",
                    )
                )
                assert ("failed to rename" in diagnostics.getvalue()) == rename_error
            payload = read_result(ctx.output_dir)
            assert payload["exit_code"] == code
            assert payload["measurement_count"] == count + 1 and payload["command_count"] == 1
            with closing(sqlite3.connect(ctx.output_dir / "execution.sqlite")) as reader:
                assert reader.execute("SELECT COUNT(*) FROM measurements").fetchone()[0] == count + 1
                assert reader.execute("SELECT status FROM verifications").fetchall() == [(status,)]
            if report_error:
                assert not (ctx.output_dir / "summary.json").exists()
            else:
                public = {
                    key: value
                    for key, value in payload.items()
                    if key not in {"outcomes", "optional_outcomes", "stored_status"}
                }
                assert json.loads((ctx.output_dir / "summary.json").read_text(encoding="utf-8")) == public
                text = (ctx.output_dir / "summary.txt").read_text(encoding="utf-8")
                assert f"Overall result: {'FAIL' if code else 'PASS'}" in text
                assert f"Exit code: {code}" in text
        finally:
            ctx.db.close()


def main() -> None:
    import atheris

    with atheris.instrument_imports(include=["colosseum"]):
        import colosseum.results.finalize  # noqa: F401
    atheris.Setup(sys.argv, atheris.instrument_func(check_input))
    atheris.Fuzz()


if __name__ == "__main__":
    main()
