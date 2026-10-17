"""Per-slot / per-run finalize policy (what side effects to run)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FinalizeKind = Literal["single", "suite_slot"]


@dataclass(frozen=True)
class FinalizePolicy:
    """Side-effect flags for one finalize call.

    Derived from session kind and whether the slot scores the suite.
    """

    kind: FinalizeKind
    write_summary: bool
    rename_dir: bool
    scores_suite: bool
    run_shutdown: bool
    close_resources: bool
    log_overall: bool


def policy_for_single(*, run_shutdown: bool = True) -> FinalizePolicy:
    return FinalizePolicy(
        kind="single",
        write_summary=True,
        rename_dir=True,
        scores_suite=True,
        run_shutdown=run_shutdown,
        close_resources=True,
        log_overall=True,
    )


def policy_for_suite_slot(*, affects_suite_result: bool) -> FinalizePolicy:
    """Suite script slots never run plugin shutdown (once at suite finalize)."""
    return FinalizePolicy(
        kind="suite_slot",
        write_summary=affects_suite_result,
        rename_dir=affects_suite_result,
        scores_suite=affects_suite_result,
        run_shutdown=False,
        close_resources=True,
        log_overall=affects_suite_result,
    )

