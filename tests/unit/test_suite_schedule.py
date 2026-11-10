"""Cycle and repeat deadlines, driven by a clock the test controls."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import colosseum.runner.suite as suite_mod
from colosseum.runner.suite_toml import SuiteDefinition, SuiteTestEntry


def _drive(monkeypatch, suite: SuiteDefinition, step: float) -> list[str]:
    clock = {"now": 0.0}
    monkeypatch.setattr(suite_mod.time, "monotonic", lambda: clock["now"])
    seen: list[str] = []

    def slot(_suite, _ctx, script: Path, _runner, **_kwargs) -> bool:
        seen.append(script.name)
        clock["now"] += step
        return False

    monkeypatch.setattr(suite_mod, "_run_script_slot", slot)
    suite_mod._run_test_schedule(suite, None, None)  # type: ignore[arg-type]
    return seen


def _suite(
    names: list[str],
    *,
    cycle_for: timedelta | None = None,
    repeat_for: timedelta | None = None,
) -> SuiteDefinition:
    return SuiteDefinition(
        name="clock",
        setup=[],
        tests=[SuiteTestEntry(path=Path(name), repeat_for=repeat_for) for name in names],
        between_tests=[],
        teardown=[],
        cycle_for=cycle_for,
    )


def test_cycle_for_finishes_the_cycle_that_meets_the_deadline(monkeypatch) -> None:
    seen = _drive(
        monkeypatch,
        _suite(["a.py", "b.py", "c.py"], cycle_for=timedelta(seconds=2)),
        step=1.0,
    )
    assert seen == ["a.py", "b.py", "c.py"]


def test_cycle_for_starts_another_full_cycle_while_time_remains(monkeypatch) -> None:
    seen = _drive(
        monkeypatch,
        _suite(["a.py", "b.py", "c.py"], cycle_for=timedelta(seconds=4)),
        step=1.0,
    )
    assert seen == ["a.py", "b.py", "c.py", "a.py", "b.py", "c.py"]


def test_repeat_for_stops_once_the_clock_reaches_the_deadline(monkeypatch) -> None:
    seen = _drive(
        monkeypatch,
        _suite(["repeat.py"], repeat_for=timedelta(seconds=2)),
        step=2.0,
    )
    assert seen == ["repeat.py"]


def test_repeat_for_continues_while_the_clock_is_before_the_deadline(monkeypatch) -> None:
    seen = _drive(
        monkeypatch,
        _suite(["repeat.py"], repeat_for=timedelta(seconds=2)),
        step=1.0,
    )
    assert seen == ["repeat.py", "repeat.py"]
