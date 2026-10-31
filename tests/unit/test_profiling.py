"""Unit tests for ``colosseum run --profile`` helpers."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType, SimpleNamespace

import colosseum.runner.profiling as profiling
import pytest


class _FakeProfiler:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def output_html(self) -> str:
        return "<html>profile</html>"

    def output_text(self, **_kwargs: object) -> str:
        return "PROFILE_TEXT"


class _FakePyinstrument:
    Profiler = _FakeProfiler


def test_require_pyinstrument_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def _fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "pyinstrument" or name.startswith("pyinstrument."):
            raise ImportError("nope")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    with pytest.raises(RuntimeError, match="pyinstrument"):
        profiling.require_pyinstrument()


def test_run_with_profile_writes_html(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = tmp_path / "run-pass"
    out.mkdir()
    monkeypatch.setattr(profiling, "require_pyinstrument", lambda: _FakePyinstrument)
    monkeypatch.setattr(
        profiling,
        "_profile_destination",
        lambda: out,
    )

    code = profiling.run_with_profile(lambda: 0, no_artifacts=False)
    assert code == 0
    html = out / "profile.html"
    assert html.read_text(encoding="utf-8") == "<html>profile</html>"
    captured = capsys.readouterr()
    assert "PROFILE_TEXT" in captured.out
    assert str(html) in captured.out


def test_run_with_profile_text_only_when_no_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(profiling, "require_pyinstrument", lambda: _FakePyinstrument)
    monkeypatch.setattr(profiling, "_profile_destination", lambda: tmp_path)

    code = profiling.run_with_profile(lambda: 7, no_artifacts=True)
    assert code == 7
    assert not (tmp_path / "profile.html").exists()
    out = capsys.readouterr().out
    assert "PROFILE_TEXT" in out
    assert "Profile written" not in out


def test_run_with_profile_coerces_system_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(profiling, "require_pyinstrument", lambda: _FakePyinstrument)
    monkeypatch.setattr(profiling, "_emit_profile", lambda *_a, **_k: None)

    def _boom() -> int:
        raise SystemExit(3)

    assert profiling.run_with_profile(_boom, no_artifacts=True) == 3


def test_profile_destination_prefers_suite_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    suite = Path("/tmp/suite-fail")
    single = Path("/tmp/slot")
    ctx = SimpleNamespace(
        no_artifacts=False,
        suite_output_dir=suite,
        output_dir=single,
    )
    monkeypatch.setattr(
        "colosseum.context.get_context",
        lambda: ctx,
    )
    assert profiling._profile_destination() == suite


def test_cli_profile_flag_registered() -> None:
    from colosseum.runner.cli import _build_parser

    parser = _build_parser()
    for command in ("run", "run-suite"):
        ns = parser.parse_args([command, "x.py" if command == "run" else "s.toml", "--profile"])
        assert ns.profile is True


def test_require_pyinstrument_returns_module(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = ModuleType("pyinstrument")
    monkeypatch.setitem(__import__("sys").modules, "pyinstrument", fake)
    assert profiling.require_pyinstrument() is fake
