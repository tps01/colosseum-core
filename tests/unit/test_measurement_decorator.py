"""U-MV-01: @measurement duplicate key rules."""

from __future__ import annotations

from contextlib import suppress
from inspect import signature

import pytest
from colosseum.decorators.measurement import MeasurementKeyError, measurement
from colosseum.decorators.verification import VerificationResult, verification


@pytest.fixture
def ctx(unit_runtime_context):
    return unit_runtime_context


@measurement
def _once(*, key: str) -> int:
    return 1


@measurement(multi_row=True)
def _multi(*, key: str, row_index: int) -> int:
    return row_index


@measurement
def _boom(*, key: str) -> int:
    raise RuntimeError("probe failed")


@measurement
def _later(*, key: str) -> int:
    return 7


@measurement
def _accepts_optional(*, key: str, optional: bool = False) -> int:
    return 1 if optional else 0


@pytest.mark.requirement("U-MV-01")
def test_duplicate_key_raises(ctx) -> None:
    _once(key="dup")
    with pytest.raises(MeasurementKeyError, match="Duplicate measurement key"):
        _once(key="dup")


def test_multi_row_requires_row_index(ctx) -> None:
    with pytest.raises(MeasurementKeyError, match="row_index"):
        _multi(key="series")


def test_multi_row_allows_distinct_indexes(ctx) -> None:
    _multi(key="series", row_index=0)
    _multi(key="series", row_index=1)
    assert ctx.db.count_rows("measurements", "key=?", ("series",)) == 2


def test_optional_keyword_is_on_the_signature() -> None:
    param = signature(_once).parameters["optional"]
    assert param.default is False
    assert param.kind.name == "KEYWORD_ONLY"
    assert list(signature(_accepts_optional).parameters).count("optional") == 1


def test_measurement_error_records_and_raises(ctx) -> None:
    with pytest.raises(RuntimeError, match="probe failed"):
        _boom(key="required")
    row = ctx.db.get_measurement("core", "_boom", "required")
    assert row is not None
    assert row.status == "ERROR"
    assert row.value is None
    assert ctx.result_aggregator.overall_pass() is False


def test_caught_measurement_error_still_fails_the_slot(ctx) -> None:
    with suppress(RuntimeError):
        _boom(key="caught")
    assert ctx.result_aggregator.overall_pass() is False
    failed = ctx.result_aggregator.failed_required_outcomes()
    assert any(row["kind"] == "measurement" and row["key"] == "caught" for row in failed)


def test_optional_measurement_error_continues_and_verification_fails(ctx) -> None:
    assert _boom(key="probe", optional=True) is None
    assert ctx.result_aggregator.overall_pass() is True
    row = ctx.db.get_measurement("core", "_boom", "probe")
    assert row is not None
    assert row.status == "ERROR"
    assert row.value is None

    @verification
    def verify_probe(*, key: str, optional: bool = False) -> VerificationResult:
        recorded = ctx.db.get_measurement("core", "_boom", key)
        if recorded is None or recorded.value is None:
            return VerificationResult(
                status="FAIL",
                message="measurement value missing",
                optional=optional,
            )
        return VerificationResult(status="PASS", message="", optional=optional)

    result = verify_probe(key="probe")
    assert result.status == "FAIL"
    assert ctx.result_aggregator.overall_pass() is False
    assert _later(key="after") == 7
    later = ctx.db.get_measurement("core", "_later", "after")
    assert later is not None
    assert later.status == "PASS"
    assert later.value == 7


def test_debug_log_lists_call_arguments(ctx) -> None:
    from colosseum.logging.setup import setup_logging

    setup_logging(ctx, console=False, file=True)
    long_note = "n" * 200

    @measurement
    def read_probe(*, key: str, note: str) -> int:
        return 1

    read_probe(key="probe", note=long_note)
    assert ctx.output_dir is not None
    text = (ctx.output_dir / "debug.log").read_text(encoding="utf-8")
    assert "'key': 'probe'" in text
    assert "'note': '" + long_note + "'" in text

    @measurement
    def fail_probe(*, key: str, password: str) -> int:
        raise RuntimeError("probe failed")

    with pytest.raises(RuntimeError, match="probe failed"):
        fail_probe(key="secret", password="super-secret")
    text = (ctx.output_dir / "debug.log").read_text(encoding="utf-8")
    assert "super-secret" not in text
    assert "***" in text


def test_missing_key_raises_when_optional(ctx) -> None:
    with pytest.raises(MeasurementKeyError, match="requires `key=`"):
        _boom(key="", optional=True)


def test_duplicate_key_raises_when_optional(ctx) -> None:
    _once(key="dup-opt")
    with pytest.raises(MeasurementKeyError, match="Duplicate measurement key"):
        _once(key="dup-opt", optional=True)
