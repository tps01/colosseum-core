"""U-MV: @verification behavior."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from colosseum.decorators.measurement import measurement
from colosseum.decorators.verification import (
    MeasurementSource,
    VerificationResult,
    _resolve_domain,
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
    assert _resolve_domain(sample) == "shared"

    monkeypatch.setattr(sample, "__module__", "colosseum_equipment.psu")
    assert _resolve_domain(sample) == "equipment"

    monkeypatch.setattr(sample, "__module__", "local_module")
    assert _resolve_domain(sample) == "core"


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
