"""U-MV: @verification behavior."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import FrozenInstanceError
from inspect import signature
from typing import Any, get_overloads, get_type_hints

import pytest

from colosseum.decorators.measurement import measurement
from colosseum.decorators._common import resolve_domain
from colosseum.decorators.command import COLOSSEUM_DECORATOR
from colosseum.decorators.verification import (
    MeasurementSource,
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


@measurement(multi_row=True)
def _capture_indexed_value(*, key: str, row_index: int) -> int:
    return row_index


@verification()
def _bool_verify(*, key: str, expected: bool, optional: bool = False) -> bool:
    return expected


@verification()
def _raises_verify(*, key: str) -> bool:
    raise RuntimeError("boom")


@pytest.mark.requirement("U-MV-02")
def test_missing_measurement_source_records_error(ctx) -> None:
    @verification(sources=[MeasurementSource(domain="equipment", command="measure_voltage")])
    def needs_measure(*, key: str) -> bool:
        return True

    result = needs_measure(key="rail_a")
    assert result.status == "ERROR"
    assert "Missing measurement source" in result.message
    assert ctx.result_aggregator.overall_pass() is False


@pytest.mark.requirement("U-MV-03")
def test_optional_failure_does_not_fail_aggregate(ctx) -> None:
    result = _bool_verify(key="opt", expected=False, optional=True)
    assert result.status == "FAIL"
    assert result.message == "verification returned False"
    assert ctx.result_aggregator.overall_pass() is True


def test_missing_key_is_error(ctx) -> None:
    result = _bool_verify(key="", expected=True)
    assert result.status == "ERROR"
    assert ctx.db.count_rows("verifications", "key=?", ("<missing>",)) >= 1


def test_exception_becomes_error_status(ctx) -> None:
    result = _raises_verify(key="x")
    assert result.status == "ERROR"
    assert "boom" in result.message


def test_optional_kwarg_requires_wrapped_parameter(ctx) -> None:
    """Document contract: optional= must be accepted by the wrapped function signature."""

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


def test_measurement_source_is_immutable() -> None:
    source = MeasurementSource(domain="core", command="read")
    with pytest.raises(FrozenInstanceError):
        source.domain = "equipment"


def test_resolve_domain_maps_plugin_module_prefixes(monkeypatch) -> None:
    def sample() -> bool:
        return True

    monkeypatch.setattr(sample, "__module__", "colosseum_shared.regex")
    assert resolve_domain(sample) == "shared"

    monkeypatch.setattr(sample, "__module__", "colosseum_equipment.psu")
    assert resolve_domain(sample) == "equipment"

    monkeypatch.setattr(sample, "__module__", "local_module")
    assert resolve_domain(sample) == "core"


def test_source_lookup_defaults_to_row_zero(ctx) -> None:
    _capture_indexed_value(key="series", row_index=1)
    _capture_indexed_value(key="series", row_index=-1)

    @verification(sources=[MeasurementSource(domain="core", command="_capture_indexed_value")])
    def needs_default_row(*, key: str) -> bool:
        return True

    result = needs_default_row(key="series")
    assert result.status == "ERROR"
    assert "Missing measurement source" in result.message


def test_verification_preserves_wrapped_function_metadata() -> None:
    @verification()
    def named_verification(*, key: str) -> bool:
        return True

    assert named_verification.__name__ == "named_verification"


def test_sources_must_be_passed_by_keyword() -> None:
    def bare(*, key: str) -> bool:
        return True

    with pytest.raises(TypeError):
        verification(bare, [])


def test_missing_measurement_result_defaults_required() -> None:
    result = missing_measurement_result(key="rail")
    assert result.optional is False
    assert signature(missing_measurement_result).parameters["optional"].default is False


def test_verification_overloads_and_annotations() -> None:
    overloads = get_overloads(verification)
    assert len(overloads) == 2
    for overload in overloads:
        assert get_type_hints(overload)["sources"] == Iterable[MeasurementSource] | None

    impl_hints = get_type_hints(verification)
    assert impl_hints["_func"] == Callable[..., Any] | None
    assert impl_hints["sources"] == Iterable[MeasurementSource] | None


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


def test_present_source_allows_verification(ctx) -> None:
    _capture_value(key="rail", value=3.3)

    @verification(sources=[MeasurementSource(domain="core", command="_capture_value")])
    def needs_measure(*, key: str) -> bool:
        return True

    result = needs_measure(key="rail")
    assert result.status == "PASS"
    assert ctx.result_aggregator.overall_pass() is True


def test_expected_val_and_minimum_persisted(ctx) -> None:
    import json

    @verification()
    def with_limits(*, key: str, expected_val: float = 0.0, minimum: float = 0.0) -> bool:
        return True

    with_limits(key="rail", expected_val=3.3)
    row = ctx.db.fetch_table_rows("verifications")[-1]
    assert json.loads(row["expected_json"]) == 3.3

    with_limits(key="rail", minimum=1.5)
    row = ctx.db.fetch_table_rows("verifications")[-1]
    assert json.loads(row["expected_json"]) == 1.5
