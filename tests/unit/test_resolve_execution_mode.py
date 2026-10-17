"""CLI execution-mode resolution matrix."""

from __future__ import annotations

from pathlib import Path

import pytest

from colosseum.runner.run_options import RunOptionsError, resolve_execution_mode

_PRIOR = Path("/tmp/prior-run")


@pytest.mark.parametrize(
    ("kwargs", "expected_mode", "expected_prior"),
    [
        ({}, "full", None),
        ({"procedure": True}, "procedure", None),
        ({"mode": "procedure"}, "procedure", None),
        ({"mode": "full"}, "full", None),
        ({"previous_output": _PRIOR}, "verify_only", _PRIOR),
        ({"mode": "verify_only", "previous_output": _PRIOR}, "verify_only", _PRIOR),
        ({"mode": "procedure", "procedure": True}, "procedure", None),
    ],
)
def test_run_mode_matrix_ok(kwargs, expected_mode, expected_prior) -> None:
    mode, prior = resolve_execution_mode(command="run", **kwargs)
    assert mode == expected_mode
    assert prior == expected_prior


@pytest.mark.parametrize(
    "kwargs",
    [
        {"mode": "verify_only"},
        {"mode": "procedure", "previous_output": _PRIOR},
        {"procedure": True, "previous_output": _PRIOR},
        {"mode": "full", "previous_output": _PRIOR},
        {"mode": "full", "procedure": True},
        {"mode": "verify_only", "procedure": True},
        {"mode": "bogus"},
    ],
)
def test_run_mode_matrix_errors(kwargs) -> None:
    with pytest.raises(RunOptionsError):
        resolve_execution_mode(command="run", **kwargs)


@pytest.mark.parametrize(
    ("kwargs", "expected_mode"),
    [
        ({}, "full"),
        ({"procedure": True}, "procedure"),
        ({"mode": "procedure"}, "procedure"),
        ({"mode": "full"}, "full"),
        ({"mode": "procedure", "procedure": True}, "procedure"),
    ],
)
def test_suite_mode_matrix_ok(kwargs, expected_mode) -> None:
    mode, prior = resolve_execution_mode(command="run-suite", **kwargs)
    assert mode == expected_mode
    assert prior is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"mode": "verify_only"},
        {"previous_output": _PRIOR},
        {"mode": "verify_only", "previous_output": _PRIOR},
        {"mode": "full", "procedure": True},
    ],
)
def test_suite_mode_matrix_errors(kwargs) -> None:
    with pytest.raises(RunOptionsError):
        resolve_execution_mode(command="run-suite", **kwargs)
