"""Reduce real finalized slots into a persistent suite container."""

from __future__ import annotations

import io
import json
import sqlite3
import sys
import tempfile
from contextlib import closing, redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tests.fuzz.disk_finalization import read_result
from tests.fuzz.results import new_context


def check_input(data: bytes) -> None:
    import colosseum.context as context_module
    from colosseum.database import DatabaseManager
    from colosseum.results.aggregation import ResultAggregator
    from colosseum.results.exit_policy import endex, finalize_suite
    from colosseum.runner.runtime import finalize_script_slot
    from colosseum.summary.writer import SuiteSummaryWriter

    flags = data[0] if data else 0
    expected, scored, failed_scored = 0, 0, 0
    calls = []
    ctx = new_context()
    ctx.session.kind, ctx.no_artifacts = "suite", False
    ctx.plugin_registry.register_shutdown(lambda: calls.append(1))
    with tempfile.TemporaryDirectory(prefix="colosseum-suite-fuzz-") as temporary:
        root = Path(temporary) / "suite"
        root.mkdir()
        ctx.suite_output_dir = root
        container = DatabaseManager()
        container.initialize(root / "execution.sqlite")
        container.close()
        try:
            with patch.object(type(ctx.session), "reattach_console", return_value=None):
                for index, opcode in enumerate(data[1:7] or b"\x01"):
                    phase = ("setup", "test", "teardown")[opcode % 3]
                    failing = bool(opcode & 8)
                    affects = phase == "test" and not opcode & 16
                    if failing and phase != "test":
                        ctx.session.mark_suite_failed(f"{phase} failure")
                        expected = 1
                    scored += affects
                    failed_scored += affects and failing
                    expected |= affects and failing
                    ctx.output_dir = root / f"slot{index}"
                    ctx.output_dir.mkdir()
                    ctx.db = DatabaseManager()
                    ctx.db.initialize(ctx.output_dir / "execution.sqlite")
                    ctx.result_aggregator = ResultAggregator()
                    ctx.result_aggregator.record_verification(
                        SimpleNamespace(
                            status="FAIL" if failing else "PASS",
                            optional=False,
                            message="fuzz",
                        ),
                        key="limit",
                        requirements=["R0"],
                    )
                    ctx.phase, ctx.slot_affects_suite_result = phase, affects
                    ctx.slot_finalized, ctx.runtime_ready = False, True
                    finalize_script_slot(
                        ctx,
                        script_path=Path(f"test{index % 2}.py"),
                        test_index=index % 2 if phase == "test" else None,
                        repeat_index=index // 2,
                    )
                    assert calls == []
            if flags & 1:
                ctx.session.mark_fail_fast_stopped(Path("test.py"), "generated stop")
                expected = 1
            diagnostics = io.StringIO()
            with (
                patch.object(context_module, "_ACTIVE_CONTEXT", ctx),
                redirect_stderr(diagnostics),
            ):
                if flags & 2:
                    with patch.object(
                        SuiteSummaryWriter,
                        "write",
                        side_effect=OSError("suite report fault"),
                    ):
                        code = finalize_suite(ctx)
                else:
                    code = finalize_suite(ctx)
                assert code == expected and ctx.finalized and ctx.suite_finalized
                assert ctx.final_exit_code == expected and calls == [1]
                try:
                    endex()
                except SystemExit as exc:
                    assert exc.code == expected
                else:
                    raise AssertionError("Completed suite endex returned")
                assert calls == [1]
            if not flags & 2:
                assert "failed to write suite summary" not in diagnostics.getvalue(), diagnostics.getvalue()
                payload = read_result(ctx.suite_output_dir)
                summary = json.loads(
                    (ctx.suite_output_dir / "summary.json").read_text(encoding="utf-8"),
                )
                assert summary == payload and payload["exit_code"] == expected
                assert payload["test_slot_counts"]["total"] == scored
                assert payload["test_slot_counts"]["fail"] == failed_scored
                assert len(payload["all_slots"]) == len(data[1:7] or b"\x01")
                with closing(sqlite3.connect(ctx.suite_output_dir / "execution.sqlite")) as reader:
                    rows = reader.execute(
                        "SELECT slot_id, output_directory FROM suite_slot_results",
                    ).fetchall()
                assert len(rows) == len(payload["all_slots"])
                assert len({row[0] for row in rows}) == len(rows)
                assert all((ctx.suite_output_dir / row[1]).is_dir() for row in rows)
                for slot in ctx.suite_slot_results:
                    assert slot.output_dir.is_relative_to(ctx.suite_output_dir)
                    if slot.affects_suite_result:
                        assert json.loads(
                            (slot.output_dir / "summary.json").read_text(encoding="utf-8"),
                        )[
                            "output_directory"
                        ] == str(slot.output_dir)
                    else:
                        assert not (slot.output_dir / "summary.json").exists()
            else:
                assert not (ctx.suite_output_dir / "summary.json").exists()
        finally:
            ctx.db.close()


def main() -> None:
    import atheris

    with atheris.instrument_imports(include=["colosseum"]):
        import colosseum.results.exit_policy  # noqa: F401
    atheris.Setup(sys.argv, atheris.instrument_func(check_input))
    atheris.Fuzz()


if __name__ == "__main__":
    main()
