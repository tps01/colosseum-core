"""U-AGG: ResultAggregator exit policy."""

from __future__ import annotations

import json

import pytest

from colosseum.decorators import CommandResult
from colosseum.decorators.verification import VerificationResult
from colosseum.results.aggregation import ResultAggregator


def _record(agg: ResultAggregator, status: str, *, optional: bool = False) -> None:
    agg.record_verification(
        VerificationResult(status=status, optional=optional),
        key="k",
        command="cmd",
        domain="core",
    )


def _record_command(agg: ResultAggregator, status: str, *, optional: bool = False) -> None:
    agg.record_command(
        CommandResult(status=status, optional=optional),
        key="ck",
        command="cmd_fn",
        domain="equipment",
    )


def test_record_verification_requires_keyword_metadata() -> None:
    agg = ResultAggregator()
    result = VerificationResult(status="PASS")
    with pytest.raises(TypeError):
        agg.record_verification(result, "k", "cmd", "core")  # type: ignore[misc]


def test_record_command_requires_keyword_metadata() -> None:
    agg = ResultAggregator()
    result = CommandResult(status="PASS")
    with pytest.raises(TypeError):
        agg.record_command(result, "k", "cmd", "core")  # type: ignore[misc]


@pytest.mark.requirement("U-AGG-01")
def test_required_fail_fails_overall() -> None:
    agg = ResultAggregator()
    _record(agg, "PASS")
    _record(agg, "FAIL", optional=False)
    assert agg.overall_pass() is False
    assert agg.exit_code() == 1


@pytest.mark.requirement("U-AGG-01")
def test_required_error_fails_overall() -> None:
    agg = ResultAggregator()
    _record(agg, "ERROR")
    assert agg.overall_pass() is False


@pytest.mark.requirement("U-AGG-01")
def test_optional_fail_does_not_fail_overall() -> None:
    agg = ResultAggregator()
    _record(agg, "PASS")
    _record(agg, "FAIL", optional=True)
    assert agg.overall_pass() is True
    assert agg.exit_code() == 0


def test_optional_failure_before_required_failure_still_fails() -> None:
    agg = ResultAggregator()
    _record(agg, "FAIL", optional=True)
    _record(agg, "FAIL", optional=False)
    assert agg.overall_pass() is False


@pytest.mark.requirement("U-AGG-02")
def test_exit_code_only_zero_or_one() -> None:
    agg = ResultAggregator()
    assert agg.exit_code() in (0, 1)
    _record(agg, "FAIL")
    assert agg.exit_code() == 1


@pytest.mark.requirement("U-AGG-03")
def test_suite_error_and_teardown_failed_force_fail() -> None:
    agg = ResultAggregator()
    _record(agg, "PASS")
    agg.mark_suite_error("setup failed")
    assert agg.overall_pass() is False
    assert agg.failed_required_outcomes()

    agg2 = ResultAggregator()
    _record(agg2, "PASS")
    agg2.mark_teardown_failed()
    assert agg2.overall_pass() is False
    assert agg2.exit_code() == 1


def test_suite_error_flag_is_recorded() -> None:
    agg = ResultAggregator()
    agg.mark_suite_error("setup failed")
    assert agg.suite_error is True


def test_failed_required_excludes_optional_passes() -> None:
    agg = ResultAggregator()
    _record(agg, "PASS", optional=True)
    _record(agg, "FAIL", optional=True)
    assert agg.failed_required_verifications() == []


def test_all_required_pass_overall() -> None:
    agg = ResultAggregator()
    _record(agg, "PASS")
    _record_command(agg, "PASS")
    assert agg.overall_pass() is True
    assert agg.exit_code() == 0


def test_failed_required_verifications_filters_by_kind() -> None:
    agg = ResultAggregator()
    _record(agg, "FAIL", optional=False)
    _record_command(agg, "FAIL", optional=False)
    failed = agg.failed_required_verifications()
    assert len(failed) == 1
    assert failed[0]["kind"] == "verification"
    assert failed[0]["key"] == "k"


def test_failed_required_commands_filters_by_kind() -> None:
    agg = ResultAggregator()
    _record(agg, "FAIL", optional=False)
    _record_command(agg, "FAIL", optional=False)
    failed = agg.failed_required_commands()
    assert len(failed) == 1
    assert failed[0]["kind"] == "command"
    assert failed[0]["key"] == "ck"


def test_optional_verifications_filters_by_kind() -> None:
    agg = ResultAggregator()
    _record(agg, "FAIL", optional=True)
    _record_command(agg, "FAIL", optional=True)
    optional = agg.optional_verifications()
    assert len(optional) == 1
    assert optional[0]["kind"] == "verification"
    assert optional[0]["optional"] is True


def test_kind_filters_use_exact_equality() -> None:
    """Reject ``is``/ordering mutants that behave like ``==`` only for interned literals."""
    agg = ResultAggregator()
    _record(agg, "FAIL", optional=False)
    _record(agg, "FAIL", optional=True)
    _record_command(agg, "FAIL", optional=False)
    _record_command(agg, "FAIL", optional=True)

    ver_fail = agg.failed_required_verifications()[0]
    ver_fail["kind"] = json.loads('"verification"')
    assert len(agg.failed_required_verifications()) == 1

    cmd_fail = agg.failed_required_commands()[0]
    cmd_fail["kind"] = json.loads('"command"')
    assert len(agg.failed_required_commands()) == 1

    opt_ver = agg.optional_verifications()[0]
    opt_ver["kind"] = json.loads('"verification"')
    assert len(agg.optional_verifications()) == 1

    opt_ver["kind"] = "verification" + "~"
    assert agg.optional_verifications() == []

    agg_ver = ResultAggregator()
    _record(agg_ver, "FAIL")
    agg_ver.failed_required_verifications()[0]["kind"] = "verification" + "~"
    assert agg_ver.failed_required_verifications() == []

    agg_cmd = ResultAggregator()
    _record_command(agg_cmd, "FAIL")
    agg_cmd.failed_required_commands()[0]["kind"] = "comman"
    assert agg_cmd.failed_required_commands() == []


def test_optional_error_does_not_fail_overall() -> None:
    agg = ResultAggregator()
    _record(agg, "PASS")
    _record(agg, "ERROR", optional=True)
    assert agg.overall_pass() is True


def test_counts_split_required_and_optional() -> None:
    agg = ResultAggregator()
    _record(agg, "PASS")
    _record(agg, "FAIL", optional=True)
    _record(agg, "FAIL", optional=False)
    counts = agg.counts()
    assert counts["required"]["PASS"] == 1
    assert counts["required"]["FAIL"] == 1
    assert counts["optional"]["FAIL"] == 1
    assert counts["total"] == 3
