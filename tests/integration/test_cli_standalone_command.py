"""Integration tests for expanded CLI run modes."""

from __future__ import annotations

import types

import pytest

from colosseum.decorators import command
from colosseum.runner.cli import run_cli
from tests.support.helpers import latest_output_dir, query_db


@pytest.mark.requirement("E2E-RUN-11")
def test_standalone_command_run_writes_artifacts(
    monkeypatch,
    isolated_cwd,
    core_config,
) -> None:
    """Standalone ``-c`` produces command evidence and artifacts."""
    module = types.ModuleType("stub_api")

    @command
    def ping(*, key: str = "") -> None:
        return None

    module.ping = ping
    module.__colosseum_domain__ = "stub"

    import colosseum.plugins.loader as loader

    class _EntryPoint:
        name = "stub"

        @staticmethod
        def load():
            def register(registry):
                registry.register_namespace("stub", module)

            return register

    monkeypatch.setattr(loader, "entry_points_for_group", lambda _group: [_EntryPoint()])

    with pytest.raises(SystemExit) as exc:
        run_cli(
            [
                "run",
                "-c",
                "stub.ping,key=dev1",
                "-g",
                str(core_config),
            ],
        )
    assert exc.value.code == 0
    run_dir = latest_output_dir(isolated_cwd)
    rows = query_db(run_dir, "SELECT command, key FROM commands")
    assert rows == [("ping", "dev1")]


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
