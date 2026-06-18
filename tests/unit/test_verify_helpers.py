"""Equipment tolerance verification helpers."""

from __future__ import annotations

import pytest

from colosseum.decorators import measurement
from colosseum_equipment.api._verify import tolerance_verifier, verify_tolerance


@pytest.fixture
def ctx(unit_runtime_context):
    return unit_runtime_context


@measurement
def _sample_measure(*, key: str, value: float) -> float:
    return value


def test_verify_tolerance_pass(ctx) -> None:
    _sample_measure(key="rail", value=3.3)
    result = verify_tolerance(
        domain="core",
        command="_sample_measure",
        key="rail",
        expected_val=3.3,
        tolerance=0.1,
    )
    assert result.status == "PASS"


def test_verify_tolerance_fail_includes_unit(ctx) -> None:
    _sample_measure(key="power", value=-10.0)
    result = verify_tolerance(
        domain="core",
        command="_sample_measure",
        key="power",
        expected_val=-5.0,
        tolerance=0.5,
        unit="dBm",
    )
    assert result.status == "FAIL"
    assert "dBm" in result.message


def test_verify_tolerance_missing_measurement(ctx) -> None:
    result = verify_tolerance(
        domain="core",
        command="_sample_measure",
        key="missing",
        expected_val=1.0,
        tolerance=0.1,
    )
    assert result.status == "ERROR"
    assert "no measurement for key=missing" in result.message


def test_tolerance_verifier_factory(ctx) -> None:
    verify_sample = tolerance_verifier("_sample_measure", name="verify_sample", domain="core")
    _sample_measure(key="k", value=2.0)
    assert verify_sample(key="k", expected_val=2.0).status == "PASS"
    assert verify_sample.__name__ == "verify_sample"
