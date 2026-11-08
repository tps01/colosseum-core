"""Integration tests for injected standalone-command failures."""

from __future__ import annotations

import pytest

from colosseum.runner.cli import run_cli


def test_standalone_command_missing_namespace_exits_one(
    monkeypatch,
    isolated_cwd,
    core_config,
) -> None:
    """Unknown ``-c`` namespace exits 1 (CommandInvokeError), not PASS."""
    _ = isolated_cwd
    import colosseum.plugins.loader as loader

    monkeypatch.setattr(loader, "entry_points_for_group", lambda _group: [])
    with pytest.raises(SystemExit) as exc:
        run_cli(
            [
                "run",
                "-c",
                "nosuch.fn",
                "-g",
                str(core_config),
                "--no-artifacts",
            ],
        )
    assert exc.value.code == 1


def test_unexpected_error_during_command_invoke_exits_one(
    monkeypatch,
    isolated_cwd,
    core_config,
) -> None:
    """Unexpected exceptions during ``-c`` mark FAIL and exit 1 via endex."""
    _ = isolated_cwd
    import colosseum.runner.cli as cli_mod

    def _boom(_ctx, _specs):
        raise RuntimeError("unexpected boom")

    monkeypatch.setattr(cli_mod, "invoke_plugin_commands", _boom)
    with pytest.raises(SystemExit) as exc:
        run_cli(
            [
                "run",
                "-c",
                "stub.ping,key=dev1",
                "-g",
                str(core_config),
                "--no-artifacts",
            ],
        )
    assert exc.value.code == 1
