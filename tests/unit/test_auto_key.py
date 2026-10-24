"""Omitted measurement and verification keys when auto_key() is enabled."""

from __future__ import annotations

import pytest
from colosseum import auto_key as exported_auto_key
from colosseum.context import auto_key
from colosseum.decorators.measurement import MeasurementKeyError, measurement
from colosseum.decorators.verification import VerificationResult, verification


@pytest.fixture
def ctx(unit_runtime_context):
    return unit_runtime_context


@measurement
def _measure(*, key: str) -> str:
    return key


@verification
def _verify(*, key: str) -> VerificationResult:
    return VerificationResult(status="PASS", message=key)


def _debug_log(ctx) -> str:
    assert ctx.output_dir is not None
    return (ctx.output_dir / "debug.log").read_text(encoding="utf-8")


def test_auto_key_is_public() -> None:
    assert exported_auto_key is auto_key


def test_auto_key_requires_runtime() -> None:
    with pytest.raises(RuntimeError, match="Runtime is not initialized"):
        auto_key()


def test_omitted_key_still_fails_without_auto_key(ctx) -> None:
    with pytest.raises(MeasurementKeyError, match="requires `key=`"):
        _measure()
    result = _verify()
    assert result.status == "ERROR"
    assert ctx.db.count_rows("verifications", "key=?", ("<missing>",)) == 1


def test_auto_key_numbers_each_family_from_one(ctx) -> None:
    auto_key()
    assert _measure() == "1"
    result = _verify()
    assert result.status == "PASS"
    assert result.message == "1"
    assert _measure(key="") == "2"
    assert ctx.db.get_measurement("core", "_measure", "1") is not None
    assert ctx.db.get_measurement("core", "_measure", "2") is not None
    assert ctx.db.count_rows("verifications", "key=?", ("1",)) == 1


def test_explicit_key_does_not_advance_the_counter(ctx) -> None:
    auto_key()
    assert _measure(key="named") == "named"
    assert _measure() == "1"
    assert ctx.db.get_measurement("core", "_measure", "named") is not None


def test_auto_key_warns_once(ctx) -> None:
    auto_key()
    _measure()
    _verify()
    _measure()
    text = _debug_log(ctx)
    assert text.count("Autokeying has taken place") == 1
    assert "due to not having the correct keys" in text
    assert "key=1" in text
    assert "key=2" in text


def test_second_auto_key_does_not_restart_numbering(ctx) -> None:
    auto_key()
    assert _measure() == "1"
    auto_key()
    assert _measure() == "2"


def test_auto_key_still_rejects_duplicate_explicit_key(ctx) -> None:
    auto_key()
    _measure()
    with pytest.raises(MeasurementKeyError, match="Duplicate measurement key"):
        _measure(key="1")


def test_auto_keyed_verification_skips_parameters_lookup(ctx) -> None:
    ctx.parameters_map = {"named": {"expected_val": 1.0}}
    auto_key()
    result = _verify()
    assert result.status == "PASS"
    assert result.message == "1"
    missing = _verify(key="absent")
    assert missing.status == "ERROR"
    assert "no section" in missing.message


def test_injected_key_is_omitted_when_the_function_does_not_declare_it(ctx) -> None:
    @measurement
    def bare_measure(*, value: int) -> int:
        return value

    @verification
    def bare_verify(*, value: int) -> bool:
        return value == 1

    auto_key()
    assert bare_measure(value=4) == 4
    row = ctx.db.get_measurement("core", "bare_measure", "1")
    assert row is not None
    assert row.value == 4
    result = bare_verify(value=1)
    assert result.status == "PASS"
    assert ctx.db.count_rows("verifications", "key=?", ("1",)) == 1


def test_skipped_calls_do_not_consume_keys(ctx) -> None:
    auto_key()
    ctx.active_execution_mode = "verify_only"
    assert _measure() is None
    ctx.active_execution_mode = "procedure"
    assert _verify() is None
    ctx.active_execution_mode = "full"
    assert _measure() == "1"
    result = _verify()
    assert result.message == "1"


def test_begin_script_slot_clears_auto_key(core_config) -> None:
    from colosseum.context import init_context
    from colosseum.runner.runtime import begin_script_slot, ensure_suite_runtime_ready

    ctx = init_context(
        test_case_name="auto_key_slot",
        suite_name="auto_key_slot",
        config_path=core_config,
        no_artifacts=True,
    )
    ensure_suite_runtime_ready(ctx, "auto_key_slot")
    ctx.auto_key_enabled = True
    ctx.next_measurement_key = 4
    ctx.next_verification_key = 5
    ctx.auto_key_warned = True
    begin_script_slot(ctx, "next", phase="test", affects_suite_result=True)
    assert ctx.auto_key_enabled is False
    assert ctx.next_measurement_key == 0
    assert ctx.next_verification_key == 0
    assert ctx.auto_key_warned is False
