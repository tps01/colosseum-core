"""Unit tests for ``colosseum run --no-sleep`` helpers."""

from __future__ import annotations

import colosseum.runner.keep_awake as keep_awake
import pytest


class _FakeRunning:
    def __init__(self) -> None:
        self.entered = False
        self.exited = False

    def __enter__(self) -> _FakeRunning:
        self.entered = True
        return self

    def __exit__(self, *_exc: object) -> None:
        self.exited = True


def test_cli_no_sleep_flag_registered() -> None:
    from colosseum.runner.cli import _build_parser

    parser = _build_parser()
    for command in ("run", "run-suite"):
        ns = parser.parse_args(
            [command, "x.py" if command == "run" else "s.toml", "--no-sleep"],
        )
        assert ns.no_sleep is True


def test_run_with_no_sleep_enters_and_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRunning()
    monkeypatch.setattr(keep_awake.keep, "running", lambda: fake)

    assert keep_awake.run_with_no_sleep(lambda: 0) == 0
    assert fake.entered is True
    assert fake.exited is True


def test_run_with_no_sleep_exits_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRunning()
    monkeypatch.setattr(keep_awake.keep, "running", lambda: fake)

    def _boom() -> int:
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError, match="fail"):
        keep_awake.run_with_no_sleep(_boom)
    assert fake.entered is True
    assert fake.exited is True


def test_run_with_no_sleep_coerces_system_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRunning()
    monkeypatch.setattr(keep_awake.keep, "running", lambda: fake)

    def _boom() -> int:
        raise SystemExit(3)

    assert keep_awake.run_with_no_sleep(_boom) == 3
    assert fake.entered is True
    assert fake.exited is True
