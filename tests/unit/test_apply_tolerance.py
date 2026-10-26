"""Unit tests for colosseum.decorators.apply_tolerance."""

from __future__ import annotations

import pytest

from colosseum.decorators import apply_tolerance


def test_numeric_band_inside_edge_outside() -> None:
    assert apply_tolerance(100.0, 100.0, 10).status == "PASS"
    assert apply_tolerance(110.0, 100.0, 10).status == "PASS"
    assert apply_tolerance(90.0, 100.0, 10).status == "PASS"
    fail = apply_tolerance(111.0, 100.0, 10)
    assert fail.status == "FAIL"
    assert fail.message == "expected 100.0 +/- 10.0, got 111.0"
    assert fail.actual == 111.0


def test_numeric_band_uses_abs_of_negative_tolerance() -> None:
    assert apply_tolerance(105.0, 100.0, -10).status == "PASS"
    assert apply_tolerance(111.0, 100.0, -10).status == "FAIL"


def test_signed_high_side_band() -> None:
    assert apply_tolerance(100.0, 100.0, "+10").status == "PASS"
    assert apply_tolerance(109.0, 100.0, "+10").status == "PASS"
    assert apply_tolerance(110.0, 100.0, "+10").status == "PASS"
    assert apply_tolerance(111.0, 100.0, "+10").status == "FAIL"
    assert apply_tolerance(99.0, 100.0, "+10").status == "FAIL"


def test_signed_low_side_band() -> None:
    assert apply_tolerance(100.0, 100.0, "-10").status == "PASS"
    assert apply_tolerance(90.0, 100.0, "-10").status == "PASS"
    assert apply_tolerance(89.0, 100.0, "-10").status == "FAIL"
    assert apply_tolerance(101.0, 100.0, "-10").status == "FAIL"


def test_bare_plus_minus_operators_vs_signed_band() -> None:
    assert apply_tolerance(101.0, 100.0, "+").status == "PASS"
    assert apply_tolerance(100.0, 100.0, "+").status == "FAIL"
    assert apply_tolerance(99.0, 100.0, "-").status == "PASS"
    assert apply_tolerance(100.0, 100.0, "-").status == "FAIL"
    assert apply_tolerance(109.0, 100.0, "+10").status == "PASS"


@pytest.mark.parametrize(
    ("tolerance", "actual", "expected_status"),
    [
        (">=", 100.0, "PASS"),
        (">=", 99.0, "FAIL"),
        ("GE", 100.0, "PASS"),
        ("<=", 100.0, "PASS"),
        ("LE", 101.0, "FAIL"),
        (">", 101.0, "PASS"),
        ("GT", 100.0, "FAIL"),
        ("<", 99.0, "PASS"),
        ("LT", 100.0, "FAIL"),
        ("==", 100.0, "PASS"),
        ("=", 100.0, "PASS"),
        ("EQ", 99.0, "FAIL"),
        ("!=", 99.0, "PASS"),
        ("<>", 100.0, "FAIL"),
        ("NE", 100.0, "FAIL"),
    ],
)
def test_operator_aliases(tolerance: str, actual: float, expected_status: str) -> None:
    assert apply_tolerance(actual, 100.0, tolerance).status == expected_status


def test_case_insensitive_word_operators() -> None:
    assert apply_tolerance(100.0, 100.0, " ge ").status == "PASS"
    assert apply_tolerance(99.0, 100.0, " != ").status == "PASS"


def test_tolerance_none_exact_match() -> None:
    assert apply_tolerance(100.0, 100.0, None).status == "PASS"
    assert apply_tolerance("up", "up", None).status == "PASS"
    fail = apply_tolerance("down", "up", None)
    assert fail.status == "FAIL"
    assert fail.message == "expected up, got down"


def test_equality_allows_non_numeric() -> None:
    assert apply_tolerance("locked", "locked", "==").status == "PASS"
    assert apply_tolerance("open", "locked", "NE").status == "PASS"


def test_non_numeric_with_ge_is_error() -> None:
    result = apply_tolerance("x", 1.0, "GE")
    assert result.status == "ERROR"
    assert "non-numeric" in result.message


def test_unknown_and_bool_tolerance_are_errors() -> None:
    unknown = apply_tolerance(1.0, 1.0, "~~")
    assert unknown.status == "ERROR"
    assert "unknown tolerance" in unknown.message
    bad = apply_tolerance(1.0, 1.0, True)
    assert bad.status == "ERROR"
    assert "unsupported tolerance" in bad.message


def test_optional_propagated() -> None:
    passed = apply_tolerance(1.0, 1.0, 0.0, optional=True)
    assert passed.optional is True
    failed = apply_tolerance(2.0, 1.0, 0.0, optional=True)
    assert failed.optional is True
    errored = apply_tolerance(1.0, 1.0, "??", optional=True)
    assert errored.optional is True
