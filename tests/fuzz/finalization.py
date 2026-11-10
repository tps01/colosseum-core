"""Controlled finalization failures, evidence barriers, and repeated endex calls."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from collections.abc import Callable

    from colosseum.context import RuntimeContext
    from colosseum.results.finalize import FinalizeRunResult
    from colosseum.results.finalize_policy import FinalizePolicy

from tests.fuzz.results import new_context


def check_input(data: bytes) -> None:
    import colosseum.context as context_module
    import colosseum.plugins.registry as registry_module
    from colosseum.database import MeasurementRow
    from colosseum.database.write_queue import WriteJob
    from colosseum.results import exit_policy
    from colosseum.results.finalize import finalize_run
    from colosseum.results.finalize_policy import policy_for_suite_slot

    flags = data[0] if data else 0
    slot = bool(flags & 1)
    storage_error = bool(flags & 16)
    blocked = bool(flags & 32) and not bool(flags & 64)
    failed = bool(flags & (2 | 128)) or blocked
    count = 1 + (data[1] % 4 if len(data) > 1 else 0)
    ctx = new_context()
    ctx.session.kind = "suite" if slot else "single"
    ctx.db.initialize(Path(":memory:"))
    hooks, closes, captured = [], [0] * count, []
    if flags & 2:
        ctx.result_aggregator.record_verification(
            SimpleNamespace(status="FAIL", optional=False, message="fuzz"),
        )
    if flags & 128:
        ctx.result_aggregator.mark_teardown_failed()
    if flags & 32:
        ctx.parameters_map = {"owed": {"expected_val": 1}}
    for index in range(count):
        ctx.db.enqueue_measurement(
            MeasurementRow(
                domain="core",
                command="sample",
                key="owed" if flags & 64 else "sample",
                row_index=index,
                value=index,
            ),
        )
    ctx.db.drain(timeout=2)

    def first_hook() -> None:
        hooks.append("first")
        ctx.db.enqueue_measurement(
            MeasurementRow(
                domain="core",
                command="shutdown",
                key="shutdown",
                value="settled",
            ),
        )

    def second_hook() -> None:
        hooks.append("second")
        if flags & 4:
            raise RuntimeError("controlled shutdown failure")

    def resource_close(index: int) -> Callable[[], None]:
        def close() -> None:
            closes[index] += 1
            if flags & 8:
                raise OSError("controlled resource failure")

        return close

    def fail_write() -> None:
        raise OSError("controlled storage failure")

    def capture(context: RuntimeContext, *, policy: FinalizePolicy) -> FinalizeRunResult:
        result = finalize_run(context, policy=policy)
        captured.append(result)
        return result

    ctx.plugin_registry.register_shutdown(first_hook)
    ctx.plugin_registry.register_shutdown(second_hook)
    ctx.resource_cache.update(
        {str(index): SimpleNamespace(close=resource_close(index)) for index in range(count)},
    )
    if storage_error:
        ctx.db._write_queue.put(WriteJob(apply=fail_write))
    silent = SimpleNamespace(exception=lambda *_args, **_kwargs: None)
    try:
        with (
            patch.object(context_module, "_ACTIVE_CONTEXT", ctx),
            patch.object(
                exit_policy,
                "finalize_run",
                side_effect=capture,
            ),
            patch.object(registry_module, "_logger", silent),
        ):
            try:
                if slot:
                    captured.append(
                        finalize_run(
                            ctx,
                            policy=policy_for_suite_slot(affects_suite_result=bool(flags & 2)),
                        ),
                    )
                else:
                    exit_policy.endex()
            except SystemExit as exc:
                assert not slot and not storage_error and exc.code == int(failed)
            except OSError as exc:
                assert storage_error and str(exc) == "controlled storage failure"
            else:
                assert slot and not storage_error
            assert not ctx.db.is_initialized()
            assert ctx.resource_cache == {}
            assert closes == [1] * count
            assert hooks == ([] if slot else ["second", "first"])
            if storage_error:
                assert not captured
            else:
                result = captured[0]
                assert result.exit_code == int(failed)
                assert result.overall == ("FAIL" if failed else "PASS")
                assert result.summary["exit_code"] == result.exit_code
                assert result.measurement_count == count + (not slot)
                assert len(result.measurements) == result.measurement_count
                owed = [row for row in result.verifications if row.command == "owed_limit"]
                assert len(owed) == int(blocked)
                assert all(row.status == "BLOCKED" for row in owed)
                assert sorted(row.value for row in result.measurements if row.command == "sample") == list(range(count))
            if not slot:
                expected_code = 1 if storage_error else int(failed)
                assert ctx.finalized and ctx.final_exit_code == expected_code
                for _ in range(2):
                    try:
                        exit_policy.endex()
                    except SystemExit as exc:
                        assert exc.code == expected_code
                    else:
                        raise AssertionError("Repeated endex did not exit")
                assert closes == [1] * count and hooks == ["second", "first"]
                assert len(captured) == int(not storage_error)
    finally:
        ctx.db.close()


def main() -> None:
    """Instrument core and run libFuzzer with the supplied limits."""
    import atheris

    with atheris.instrument_imports(include=["colosseum"]):
        import colosseum.results.finalize  # noqa: F401
    atheris.Setup(sys.argv, atheris.instrument_func(check_input))
    atheris.Fuzz()


if __name__ == "__main__":
    main()
