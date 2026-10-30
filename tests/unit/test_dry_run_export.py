"""Dry-run policies and parameter export collection."""

from __future__ import annotations

from pathlib import Path

import pytest

from colosseum.config.parameters import write_parameters_file
from colosseum.results.finalize import _insert_blocked_owed_keys
from colosseum.context import auto_key
from colosseum.decorators import VerificationResult, command, measurement, verification
from colosseum.decorators._common import DRY_RUN_ATTR
from colosseum.runner.cli import finish_parameter_export

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


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
    assert any("no measurement in this walk yet" in tip for tip in ctx.dry_run_tips)


def test_finalize_dry_run_tips_unused_parameters_and_empty_walk(unit_runtime_context) -> None:
    from colosseum.decorators._common import finalize_dry_run_tips

    ctx = unit_runtime_context
    ctx.run_options.dry_run = True
    ctx.parameters_map = {"stale": {"value": 1.0}}
    finalize_dry_run_tips(ctx)
    assert any("unused section" in tip for tip in ctx.dry_run_tips)
    assert any("no command/measurement/verification" in tip for tip in ctx.dry_run_tips)


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
    assert any("verification omitted key=" in tip for tip in ctx.dry_run_tips)


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


def test_dry_run_checks_argument_types(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.run_options.dry_run = True

    @command
    def label(*, text: str, note) -> None:  # noqa: ANN001
        raise AssertionError("body ran")

    @command
    def wait(*, timeout: float) -> None:
        raise AssertionError("body ran")

    assert label(text=1, note=object()) is None
    assert label(text="ok", note=object()) is None
    assert wait(timeout="61s") is None
    assert wait(timeout="nope") is None
    records = ctx.result_aggregator._records  # noqa: SLF001
    assert [row["status"] for row in records] == ["ERROR", "DRY", "DRY", "ERROR"]
    assert "text" in records[0]["message"]
    assert "duration" in records[3]["message"]


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
    blocked = [
        row["key"]
        for row in ctx.result_aggregator._records  # noqa: SLF001
        if row["status"] == "BLOCKED"
    ]
    assert blocked == ["missed"]


def test_dry_run_policy_must_be_log_call_or_callable() -> None:
    with pytest.raises(TypeError, match="dry_run"):

        @command(dry_run=1)
        def ping(*, message: str) -> None:
            return None


def test_export_merges_keyed_kwargs_and_skips_bookkeeping(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.parameter_export = {}

    @command
    def note(*, message: str) -> None:
        raise AssertionError("body ran")

    @measurement
    def capture(*, key: str, value: float) -> float:
        raise AssertionError("body ran")

    @verification
    def check(
        *,
        key: str,
        expected_val: float,
        tolerance: float = 0.0,
        optional: bool = False,
    ) -> VerificationResult:
        raise AssertionError("body ran")

    assert note(message="hello") is None
    assert capture(key="rx_level", value=0.0) is None
    assert check(
        key="rx_level",
        expected_val=1.5,
        tolerance=0.25,
        optional=True,
        description="level",
        row_index=3,
    ) is None
    assert ctx.parameter_export == {
        "rx_level": {
            "value": 0.0,
            "expected_val": 1.5,
            "tolerance": 0.25,
            "optional": True,
            "description": "level",
        },
    }
    assert ctx.export_errors == []


def test_export_records_missing_keys_and_keeps_walking(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.parameter_export = {}

    @measurement
    def capture(*, key: str, value: float) -> float:
        raise AssertionError("body ran")

    @verification
    def check(*, key: str, expected_val: float) -> VerificationResult:
        raise AssertionError("body ran")

    assert capture(value=1.0) is None
    assert check(expected_val=1.0) is None
    assert capture(key="ok", value=2.0) is None
    assert len(ctx.export_errors) == 1
    assert "was missing a key" in ctx.export_errors[0]
    assert "col.auto_key()" in ctx.export_errors[0]
    assert ctx.parameter_export == {"ok": {"value": 2.0}}


def test_export_uses_auto_key(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.parameter_export = {}
    auto_key()

    @measurement
    def capture(*, key: str, value: float) -> float:
        raise AssertionError("body ran")

    assert capture(value=1.25) is None
    assert ctx.parameter_export == {"1": {"value": 1.25}}


def test_export_rejects_values_that_are_not_toml(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.parameter_export = {}

    @command
    def tagged(*, key: str, payload: object) -> None:
        raise AssertionError("body ran")

    assert tagged(key="rx_level", payload=object()) is None
    assert any("payload" in message for message in ctx.export_errors)
    assert "payload" not in ctx.parameter_export["rx_level"]


def test_write_parameters_file_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "parameters.toml"
    write_parameters_file(
        path,
        {
            "rx_level": {
                "value": 0.0,
                "enabled": True,
                "notes": 'a "b"',
                "limits": [1, 2],
                "nested": {"unit": "V"},
            },
        },
    )
    loaded = tomllib.loads(path.read_text(encoding="utf-8"))
    assert loaded["rx_level"]["value"] == 0.0
    assert loaded["rx_level"]["enabled"] is True
    assert loaded["rx_level"]["notes"] == 'a "b"'
    assert loaded["rx_level"]["limits"] == [1, 2]
    assert loaded["rx_level"]["nested"] == {"unit": "V"}


def test_write_parameters_file_round_trips_unicode_keys_and_controls(tmp_path: Path) -> None:
    from colosseum.config.parameters import load_parameters_file

    path = tmp_path / "parameters.toml"
    tables = {
        "rail": {
            "温度": 25,
            "expected": "ready\x1b[0m",
            "nested": {"µV": 1, "ctrl": "\x00\x07\x08\x0b\x0c\x1f\x7f"},
        },
    }
    write_parameters_file(path, tables)
    loaded = load_parameters_file(path)
    assert loaded == tables


def test_finish_writes_parameters_without_a_summary(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.parameter_export = {"rx_level": {"value": 1.0}}
    assert ctx.output_dir is not None
    code = finish_parameter_export(ctx, failed=False)
    assert code == 0
    assert (ctx.output_dir / "parameters.toml").is_file()
    assert not (ctx.output_dir / "summary.txt").exists()


def test_finish_skips_the_file_when_export_failed(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    ctx.parameter_export = {"rx_level": {"value": 1.0}}
    ctx.export_errors.append(
        "`capture` measurement was missing a key; "
        "pass key=... or call col.auto_key() near the start of main()"
    )
    assert ctx.output_dir is not None
    code = finish_parameter_export(ctx, failed=False)
    assert code == 1
    assert not (ctx.output_dir / "parameters.toml").exists()
