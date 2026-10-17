"""FinalizePolicy flags for single runs vs suite slots."""

from __future__ import annotations

from colosseum.results.finalize_policy import (
    policy_for_single,
    policy_for_suite_slot,
)


def test_single_policy_runs_shutdown_and_writes() -> None:
    policy = policy_for_single(run_shutdown=True)
    assert policy.kind == "single"
    assert policy.write_summary is True
    assert policy.rename_dir is True
    assert policy.scores_suite is True
    assert policy.run_shutdown is True
    assert policy.close_resources is True


def test_scoring_slot_writes_summary_without_shutdown() -> None:
    policy = policy_for_suite_slot(affects_suite_result=True)
    assert policy.kind == "suite_slot"
    assert policy.write_summary is True
    assert policy.rename_dir is True
    assert policy.scores_suite is True
    assert policy.run_shutdown is False
    assert policy.close_resources is True


def test_supporting_slot_skips_summary_and_rename() -> None:
    policy = policy_for_suite_slot(affects_suite_result=False)
    assert policy.write_summary is False
    assert policy.rename_dir is False
    assert policy.scores_suite is False
    assert policy.run_shutdown is False
    assert policy.close_resources is True
