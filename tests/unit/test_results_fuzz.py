"""Replay result fuzz corpora without a fuzzing-engine dependency."""

from importlib import import_module
from pathlib import Path

import pytest


@pytest.mark.parametrize("target", ["results", "finalization", "disk_finalization", "suite_finalization"])
def test_results_fuzz_seeds(target):
    check = import_module(f"tests.fuzz.{target}").check_input
    for seed in (Path(__file__).parents[1] / "fuzz" / f"{target}_corpus").iterdir():
        check(seed.read_bytes())
