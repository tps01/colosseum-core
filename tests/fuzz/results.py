"""Independent scoring/count model and summary-purity checks."""

from __future__ import annotations

import copy
import json
import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from colosseum.context import RuntimeContext


def new_context() -> RuntimeContext:
    """Build an isolated core context without startup, plugins, or global state."""
    from colosseum.context import RuntimeContext
    from colosseum.database import DatabaseManager
    from colosseum.plugins.registry import PluginRegistry
    from colosseum.results.aggregation import ResultAggregator

    return RuntimeContext(
        config=None,
        output_dir=None,
        db=DatabaseManager(),
        logger=None,
        plugin_registry=PluginRegistry(),
        result_aggregator=ResultAggregator(),
        test_case_name="fuzz",
        suite_name=None,
        config_path=None,
        framework_version="fuzz",
        no_artifacts=True,
        runtime_ready=True,
    )


def check_input(data: bytes) -> None:
    from colosseum.results.aggregation import build_run_summary

    message = data[32:96].decode("utf-8", errors="replace")
    baseline = None
    for sequence in (data[:32], data[:32][::-1]):
        ctx = new_context()
        agg = ctx.result_aggregator
        counts = {"required": {}, "optional": {}, "total": 0}
        typed = {kind: {"required": {}, "optional": {}} for kind in ("verification", "command")}
        failed, measurements, commands = False, 0, 0
        suite_error, teardown = False, False
        for index, opcode in enumerate(sequence):
            action = opcode % 5
            if action == 4:
                agg.mark_teardown_failed()
                teardown, failed = True, True
                continue
            if action == 3:
                agg.mark_suite_error(message)
                kind, status, optional = "suite", "ERROR", False
                suite_error, failed = True, True
            else:
                kind = ("verification", "command", "measurement")[action]
                status = ("PASS", "FAIL", "ERROR", "BLOCKED", "DRY")[(opcode // 5) % 5]
                optional = bool(opcode & 128)
                kwargs = {"key": f"key{index % 3}", "command": "sample", "domain": "core"}
                if kind == "verification":
                    kwargs["requirements"] = ["R0", "R0", f"R{index % 2}"]
                getattr(agg, f"record_{kind}")(
                    SimpleNamespace(status=status, optional=optional, message=message),
                    **kwargs,
                )
                failed |= not optional and status in ("FAIL", "ERROR", "BLOCKED")
                measurements += kind == "measurement"
                commands += kind == "command"
            bucket = "optional" if optional else "required"
            counts[bucket][status] = counts[bucket].get(status, 0) + 1
            counts["total"] += 1
            if kind in typed:
                typed[kind][bucket][status] = typed[kind][bucket].get(status, 0) + 1
            assert agg.overall_pass() is (not failed)
            assert agg.exit_code() == int(failed)
            assert agg.counts() == counts
        assert agg.exit_code() == int(failed)
        if baseline is None:
            baseline = (counts, failed)
        else:
            assert (counts, failed) == baseline
        before = copy.deepcopy(agg._records)
        for _ in range(2):
            summary = build_run_summary(
                ctx, agg, measurement_count=measurements, command_count=commands,
            )
            assert summary["exit_code"] == int(failed)
            assert summary["overall_result"] == ("FAIL" if failed else "PASS")
            assert summary["verification_counts"] == typed["verification"]
            assert summary["command_counts"] == typed["command"]
            assert summary["measurement_count"] == measurements
            assert summary["command_count"] == commands
            assert summary["suite_error"] == suite_error
            assert summary["teardown_failed"] == teardown
            assert summary["outcomes"] == before
            assert agg._records == before
            json.dumps(summary)  # Summaries must remain JSON serializable.
        agg.record_verification(SimpleNamespace(status="PASS", optional=False, message=""))
        assert agg.exit_code() == int(failed)


def main() -> None:
    """Instrument core and run libFuzzer with the supplied limits."""
    import atheris

    with atheris.instrument_imports(include=["colosseum"]):
        import colosseum.results.aggregation  # noqa: F401
    atheris.Setup(sys.argv, atheris.instrument_func(check_input))
    atheris.Fuzz()


if __name__ == "__main__":
    main()
