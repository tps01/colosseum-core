"""U-MV: @verification behavior."""

from __future__ import annotations

import sys
import types
from inspect import signature

import pytest

from colosseum.decorators._common import resolve_domain
from colosseum.decorators.command import COLOSSEUM_DECORATOR
from colosseum.decorators.measurement import measurement
from colosseum.decorators.verification import (
    VerificationResult,
    missing_measurement_result,
    verification,
)


@pytest.fixture
def ctx(unit_runtime_context):
    return unit_runtime_context


@measurement
def _capture_value(*, key: str, value: float) -> float:
    return value


@verification()
def _bool_verify(*, key: str, expected: bool, optional: bool = False) -> bool:
    return expected


@verification()
def _raises_verify(*, key: str) -> bool:
    raise RuntimeError("boom")


@pytest.mark.requirement("U-MV-02")
def test_missing_measurement_in_body_records_error(ctx) -> None:
    @verification
    def needs_measure(*, key: str, optional: bool = False) -> VerificationResult:
        row = ctx.db.get_measurement("equipment", "measure_voltage", key, row_index=0)
        if row is None:
            return missing_measurement_result(key=key, optional=optional)
        return VerificationResult(status="PASS", message="", optional=optional)

    result = needs_measure(key="rail_a")
    assert result.status == "ERROR"
    assert "no measurement" in result.message
    assert ctx.result_aggregator.overall_pass() is False


@pytest.mark.requirement("U-MV-03")
def test_optional_failure_does_not_fail_aggregate(ctx) -> None:
    result = _bool_verify(key="opt", expected=False, optional=True)
    assert result.status == "FAIL"
    assert result.message == "verification returned False"
    assert ctx.result_aggregator.overall_pass() is True


def test_missing_key_warns_and_runs(ctx) -> None:
    from colosseum.logging.setup import setup_logging

    setup_logging(ctx, console=False, file=True)
    result = _bool_verify(key="", expected=True)
    assert result.status == "PASS"
    assert ctx.db.count_rows("verifications", "key=?", ("",)) >= 1
    assert ctx.output_dir is not None
    debug = (ctx.output_dir / "debug.log").read_text(encoding="utf-8")
    assert "verification omitted key=" in debug


def test_author_can_require_key_in_body(ctx) -> None:
    @verification
    def needs_key(*, key: str, optional: bool = False) -> VerificationResult:
        if not key:
            return missing_measurement_result(key=key, optional=optional)
        return VerificationResult(status="PASS", message="", optional=optional)

    result = needs_key(key="")
    assert result.status == "ERROR"
    assert "no measurement for key=" in result.message


def test_keyless_verification_without_key_parameter(ctx) -> None:
    @verification
    def spot_check() -> bool:
        return True

    result = spot_check()
    assert result.status == "PASS"
    assert ctx.db.count_rows("verifications", "key=?", ("",)) >= 1


def test_exception_becomes_error_status(ctx) -> None:
    result = _raises_verify(key="x")
    assert result.status == "ERROR"
    assert "boom" in result.message


def test_optional_kwarg_requires_wrapped_parameter(ctx) -> None:
    """Document specification: optional= must be accepted by the wrapped function signature."""

    @verification()
    def no_optional_param(*, key: str) -> bool:
        return False

    result = no_optional_param(key="k", optional=True)
    assert result.status == "ERROR"
    assert "optional" in result.message.lower() or "unexpected" in result.message.lower()


def test_verification_result_passthrough(ctx) -> None:
    @verification()
    def explicit(*, key: str) -> VerificationResult:
        return VerificationResult(status="FAIL", message="custom", optional=False)

    result = explicit(key="k1")
    assert result.message == "custom"
    assert ctx.result_aggregator.overall_pass() is False


def test_default_verification_result_is_required() -> None:
    assert VerificationResult(status="PASS").optional is False


def test_resolve_domain_maps_plugin_package_attribute(monkeypatch) -> None:
    plugin = types.ModuleType("acme_plugin")
    plugin.__colosseum_domain__ = "acme"  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "acme_plugin", plugin)

    def sample() -> bool:
        return True

    monkeypatch.setattr(sample, "__module__", "acme_plugin.api")
    assert resolve_domain(sample) == "acme"

    monkeypatch.setattr(sample, "__module__", "local_module")
    assert resolve_domain(sample) == "core"


def test_verification_preserves_wrapped_function_metadata() -> None:
    @verification()
    def named_verification(*, key: str) -> bool:
        return True

    assert named_verification.__name__ == "named_verification"


def test_missing_measurement_result_defaults_required() -> None:
    result = missing_measurement_result(key="rail")
    assert result.optional is False
    assert signature(missing_measurement_result).parameters["optional"].default is False


def test_verification_overloads_and_annotations() -> None:
    impl = verification.__annotations__
    assert impl["_func"] == "Callable[..., Any] | None"
    assert "sources" not in impl

    if sys.version_info < (3, 11):
        pytest.skip("typing.get_overloads requires Python 3.11+")

    from typing import get_overloads

    overloads = get_overloads(verification)
    assert len(overloads) == 2
    for overload in overloads:
        assert "sources" not in overload.__annotations__


def test_decorator_metadata() -> None:
    assert getattr(_bool_verify, COLOSSEUM_DECORATOR) == "verification"


def test_bool_pass_records_verification_row(ctx) -> None:
    result = _bool_verify(key="rail", expected=True)
    assert result.status == "PASS"
    row = ctx.db.fetch_table_rows("verifications")[-1]
    assert row["key"] == "rail"
    assert row["status"] == "PASS"
    assert ctx.result_aggregator.overall_pass() is True


def test_non_bool_return_becomes_pass_with_message(ctx) -> None:
    @verification()
    def returns_text(*, key: str) -> str:
        return "ok"

    result = returns_text(key="k")
    assert result.status == "PASS"
    assert result.message == "ok"


def test_verification_reads_prior_measurement(ctx) -> None:
    _capture_value(key="rail", value=3.3)

    @verification
    def needs_measure(*, key: str, optional: bool = False) -> VerificationResult:
        row = ctx.db.get_measurement("core", "_capture_value", key, row_index=0)
        if row is None:
            return missing_measurement_result(key=key, optional=optional)
        return VerificationResult(status="PASS", message="", optional=optional)

    result = needs_measure(key="rail")
    assert result.status == "PASS"
    assert ctx.result_aggregator.overall_pass() is True


def test_expected_val_and_minimum_persisted(ctx) -> None:
    import json

    @verification()
    def with_limits(
        *,
        key: str,
        expected_val: float = 0.0,
        tolerance: float | str | None = None,
        minimum: float = 0.0,
    ) -> bool:
        return True

    with_limits(key="rail", expected_val=3.3)
    row = ctx.db.fetch_table_rows("verifications")[-1]
    assert json.loads(row["expected_json"]) == 3.3
    assert row["compare_op"] == "EQ"
    assert row["tolerance_json"] == "null"

    with_limits(key="rail", expected_val=3.3, tolerance=0.1)
    row = ctx.db.fetch_table_rows("verifications")[-1]
    assert row["compare_op"] == "GELE"
    assert json.loads(row["tolerance_json"]) == 0.1

    with_limits(key="rail", minimum=1.5)
    row = ctx.db.fetch_table_rows("verifications")[-1]
    assert json.loads(row["expected_json"]) == 1.5
    assert row["compare_op"] == "GE"


def test_maximum_exact_and_log_compare_ops_persisted(ctx) -> None:
    import json

    @verification()
    def with_limits(
        *,
        key: str,
        maximum: float = 0.0,
        exact: float = 0.0,
        compare_op: str | None = None,
    ) -> bool:
        return True

    with_limits(key="le", maximum=5.0)
    row = ctx.db.fetch_table_rows("verifications")[-1]
    assert json.loads(row["expected_json"]) == 5.0
    assert row["compare_op"] == "LE"

    with_limits(key="eq", exact=10.0)
    row = ctx.db.fetch_table_rows("verifications")[-1]
    assert json.loads(row["expected_json"]) == 10.0
    assert row["compare_op"] == "EQ"

    with_limits(key="log", compare_op="LOG")
    row = ctx.db.fetch_table_rows("verifications")[-1]
    assert row["expected_json"] == "null"
    assert row["compare_op"] == "LOG"


def test_auto_compares_returned_value_to_expected_val(ctx) -> None:
    @measurement
    def capture(*, key: str, value: float) -> float:
        return value

    @verification()
    def check(*, key: str, expected_val: float, tolerance: float = 0.0) -> float:
        row = ctx.db.get_measurement("core", "capture", key)
        assert row is not None
        return float(row.value)

    capture(key="rail", value=3.25)
    passed = check(key="rail", expected_val=3.3, tolerance=0.1)
    assert passed.status == "PASS"
    assert passed.actual == 3.25

    capture(key="rail_hi", value=3.5)
    failed = check(key="rail_hi", expected_val=3.3, tolerance=0.1)
    assert failed.status == "FAIL"
    assert failed.actual == 3.5


def test_auto_compares_expected_result_alias(ctx) -> None:
    import json

    @verification()
    def check(*, key: str, expected_result: float, tolerance: float = 0.0) -> float:
        return 3.25

    passed = check(key="rail", expected_result=3.3, tolerance=0.1)
    assert passed.status == "PASS"
    assert passed.actual == 3.25
    row = ctx.db.fetch_table_rows("verifications")[-1]
    assert json.loads(row["expected_json"]) == 3.3
    assert row["compare_op"] == "GELE"
    assert json.loads(row["tolerance_json"]) == 0.1

    failed = check(key="rail_hi", expected_result=3.3, tolerance=0.01)
    assert failed.status == "FAIL"


def test_auto_exact_match_when_tolerance_omitted(ctx) -> None:
    @verification()
    def check(*, key: str, expected_val: float) -> float:
        return 3.3

    result = check(key="exact", expected_val=3.3)
    assert result.status == "PASS"
    assert ctx.db.fetch_table_rows("verifications")[-1]["compare_op"] == "EQ"

    result = check(key="miss", expected_val=3.4)
    assert result.status == "FAIL"


def test_auto_operator_tolerance_string(ctx) -> None:
    import json

    @verification()
    def check(*, key: str, expected_val: float, tolerance: str) -> float:
        return 5.0

    result = check(key="ge", expected_val=3.0, tolerance="GE")
    assert result.status == "PASS"
    row = ctx.db.fetch_table_rows("verifications")[-1]
    assert row["compare_op"] == "GE"
    assert row["tolerance_json"] == "null"

    result = check(key="plus", expected_val=0.0, tolerance="+10")
    assert result.status == "PASS"
    row = ctx.db.fetch_table_rows("verifications")[-1]
    assert row["compare_op"] == "GELE"
    assert json.loads(row["tolerance_json"]) == "+10"


def test_bool_return_still_explicit_pass_fail(ctx) -> None:
    @verification()
    def check(*, key: str, expected_val: float) -> bool:
        return True

    result = check(key="bool", expected_val=99.0)
    assert result.status == "PASS"
    assert result.actual is None


def test_description_persisted_without_parameter(ctx) -> None:
    @verification()
    def named(*, key: str) -> bool:
        return True

    assert signature(named).parameters["description"].default == ""
    named(key="rail", description="Verify rail voltage")
    row = ctx.db.fetch_table_rows("verifications")[-1]
    assert row["description"] == "Verify rail voltage"
    assert row["status"] == "PASS"


def test_blank_description_stores_null(ctx) -> None:
    @verification()
    def named(*, key: str) -> bool:
        return True

    named(key="rail", description="  ")
    row = ctx.db.fetch_table_rows("verifications")[-1]
    assert row["description"] is None


def test_debug_log_lists_call_arguments(ctx) -> None:
    from colosseum.logging.setup import setup_logging

    setup_logging(ctx, console=False, file=True)
    long_note = "n" * 200

    @verification()
    def named(*, key: str, note: str) -> bool:
        return True

    named(key="rail", note=long_note, description="Verify rail voltage")
    assert ctx.output_dir is not None
    text = (ctx.output_dir / "debug.log").read_text(encoding="utf-8")
    assert "'key': 'rail'" in text
    assert "'note': '" + long_note + "'" in text
    assert "'description': 'Verify rail voltage'" in text

    @verification()
    def secret(*, key: str, password: str) -> bool:
        raise RuntimeError("auth failed")

    secret(key="auth", password="super-secret")
    text = (ctx.output_dir / "debug.log").read_text(encoding="utf-8")
    assert "super-secret" not in text
    assert "***" in text
