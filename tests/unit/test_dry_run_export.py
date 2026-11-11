"""Dry-run policies and structure checks."""

from __future__ import annotations

import pytest

from colosseum.results.finalize import _insert_blocked_owed_keys
from colosseum.decorators import VerificationResult, command, measurement, verification
from colosseum.decorators._common import DRY_RUN_ATTR


def test_dry_run_log_skips_the_body(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.run_options.dry_run = True
    called = False

    @command
    def ping(*, message: str) -> None:
        nonlocal called
        called = True

    assert getattr(ping, DRY_RUN_ATTR) == "log"
    assert ping(message="hi") is None
    assert called is False
    assert ctx.result_aggregator._records[0]["status"] == "DRY"  # noqa: SLF001
    assert ctx.result_aggregator.overall_pass()
    assert ctx.db.count_rows("commands") == 0


def test_dry_run_call_runs_the_body(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.run_options.dry_run = True

    @measurement(dry_run="call")
    def capture(*, key: str, value: float) -> float:
        return value

    assert capture(key="a", value=2.0) == 2.0
    assert ctx.db.get_measurement("core", "capture", "a") is not None


def test_dry_run_substitute_runs_instead_of_the_body(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.run_options.dry_run = True

    def probe(*, message: str) -> str:
        return f"saw {message}"

    @command(dry_run=probe)
    def ping(*, message: str) -> None:
        raise AssertionError("body ran")

    assert ping(message="hi") == "saw hi"
    assert ctx.db.count_rows("commands") == 0
    assert ctx.result_aggregator._records[0]["status"] == "DRY"  # noqa: SLF001


def test_dry_run_substitute_error_is_recorded_and_reraised(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.run_options.dry_run = True

    def probe(*, message: str) -> None:
        raise RuntimeError("no instrument")

    @command(dry_run=probe)
    def ping(*, message: str) -> None:
        raise AssertionError("body ran")

    with pytest.raises(RuntimeError, match="no instrument"):
        ping(message="x")
    assert ctx.result_aggregator._records[-1]["status"] == "ERROR"  # noqa: SLF001
    assert ctx.result_aggregator.overall_pass() is False


def test_dry_run_missing_key_does_not_stop_the_walk(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.run_options.dry_run = True

    @measurement
    def capture(*, key: str, value: float) -> float:
        raise AssertionError("body ran")

    assert capture(value=1.0) is None
    assert capture(key="later", value=2.0) is None
    records = ctx.result_aggregator._records  # noqa: SLF001
    statuses = [row["status"] for row in records]
    assert statuses == ["ERROR", "DRY"]
    assert "was missing a key" in records[0]["message"]
    assert "col.auto_key()" in records[0]["message"]
    assert ctx.result_aggregator.overall_pass() is False


def _statuses(ctx) -> list[str]:
    return [row["status"] for row in ctx.result_aggregator._records]  # noqa: SLF001


def test_dry_run_rejects_duplicate_and_missing_row_index(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.run_options.dry_run = True

    @measurement
    def capture(*, key: str, value: float) -> float:
        raise AssertionError("body ran")

    @measurement(multi_row=True)
    def rows(*, key: str, value: float, row_index: int) -> float:
        raise AssertionError("body ran")

    assert capture(key="level", value=1.0) is None
    assert capture(key="level", value=2.0) is None
    assert rows(key="sweep", value=1.0) is None
    assert rows(key="sweep", value=1.0, row_index=0) is None
    assert rows(key="sweep", value=2.0, row_index=0) is None
    assert rows(key="sweep", value=3.0, row_index=1) is None
    assert _statuses(ctx) == ["DRY", "ERROR", "ERROR", "DRY", "ERROR", "DRY"]
    messages = [row["message"] for row in ctx.result_aggregator._records]  # noqa: SLF001
    assert "Duplicate measurement key" in messages[1]
    assert "multi_row=True" in messages[1]
    assert "row_index" in messages[2]
    assert "row_index=0" in messages[4]
    assert "unique key=" in messages[4] or "distinct row_index=" in messages[4]
    assert ctx.result_aggregator.overall_pass() is False


def test_dry_run_allows_verification_before_measurement(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.run_options.dry_run = True

    @measurement
    def capture(*, key: str, value: float) -> float:
        raise AssertionError("body ran")

    @verification
    def check(*, key: str, expected_val: float) -> VerificationResult:
        raise AssertionError("body ran")

    assert check(key="late", expected_val=1.0) is None
    assert capture(key="late", value=1.0) is None
    assert check(key="late", expected_val=1.0) is None
    assert _statuses(ctx) == ["DRY", "DRY", "DRY"]


def test_dry_run_allows_keyless_verification(unit_runtime_context) -> None:
    from colosseum.logging.setup import setup_logging

    ctx = unit_runtime_context
    ctx.run_options.dry_run = True
    setup_logging(ctx, console=False, file=True)

    @verification
    def spot_check(*, path: str) -> VerificationResult:
        raise AssertionError("body ran")

    assert spot_check(path="uut.log") is None
    assert _statuses(ctx) == ["DRY"]
    assert ctx.output_dir is not None
    log_text = (ctx.output_dir / "debug.log").read_text(encoding="utf-8")
    assert "verification omitted key=" in log_text
    assert "assigned an auto key" in log_text
    records = [row for row in ctx.result_aggregator._records if row.get("kind") == "verification"]  # noqa: SLF001
    assert records and records[0].get("key") == "1"


def test_dry_run_parameters_key_fills_description(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.run_options.dry_run = True
    ctx.parameters_map = {
        "logfile": {"pattern": "ERROR", "path": "uut.log", "description": "from file"},
    }

    @verification
    def check(*, key: str, pattern: str, path: str, description: str = "") -> VerificationResult:
        raise AssertionError("body ran")

    assert check(key="logfile", description="from call") is None
    assert check(key="other", pattern="x", path="y") is None
    assert _statuses(ctx) == ["DRY", "DRY"]
    records = ctx.result_aggregator._records  # noqa: SLF001
    assert records[0]["description"] == "from file"


def test_dry_run_fills_parameters_then_checks_the_signature(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.run_options.dry_run = True
    ctx.parameters_map = {"rx_level": {"expected_val": 0.0, "tolerance": 0.5}}

    @measurement
    def capture(*, key: str, value: float) -> float:
        raise AssertionError("body ran")

    @verification
    def check(*, key: str, expected_val: float, tolerance: float) -> VerificationResult:
        raise AssertionError("body ran")

    @verification
    def note(*, key: str, comment: str = "ok") -> VerificationResult:
        raise AssertionError("body ran")

    @command
    def ping(*, message: str) -> None:
        raise AssertionError("body ran")

    assert capture(key="rx_level", value=0.0) is None
    assert check(key="rx_level") is None
    assert note(key="rx_level") is None
    assert capture(key="other", value=1.0) is None
    assert check(key="other", expected_val=1.0, tolerance=0.1) is None
    assert ping() is None
    assert ping(message="hi", extra=1) is None
    assert ping(message="ok") is None
    assert _statuses(ctx) == ["DRY", "DRY", "DRY", "DRY", "DRY", "ERROR", "ERROR", "DRY"]
    messages = [row["message"] for row in ctx.result_aggregator._records]  # noqa: SLF001
    assert "message" in messages[5]
    assert "unexpected keyword" in messages[6]


def test_dry_run_owed_limit_blocks_only_unmeasured_keys(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.run_options.dry_run = True
    ctx.parameters_map = {
        "seen": {"expected_val": 1.0, "tolerance": 0.1},
        "missed": {"expected_val": 2.0, "tolerance": 0.1},
    }

    @measurement
    def capture(*, key: str, value: float) -> float:
        raise AssertionError("body ran")

    assert capture(key="seen", value=1.0) is None
    _insert_blocked_owed_keys(ctx)
    blocked = [row["key"] for row in ctx.result_aggregator._records if row["status"] == "BLOCKED"]  # noqa: SLF001
    assert blocked == ["missed"]


def test_dry_run_policy_must_be_log_call_or_callable() -> None:
    with pytest.raises(TypeError, match="dry_run"):

        @command(dry_run=1)
        def ping(*, message: str) -> None:
            return None
