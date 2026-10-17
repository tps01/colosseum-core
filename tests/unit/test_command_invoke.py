"""Unit tests for plugin command CLI parsing and invocation."""

from __future__ import annotations

import types

import pytest

from colosseum.decorators import command
from colosseum.plugins.registry import PluginRegistry
from colosseum.runner.command_invoke import (
    CommandInvokeError,
    command_logical_name,
    invoke_plugin_commands,
    parse_plugin_command,
    resolve_plugin_command,
)


def test_parse_plugin_command_with_kwargs() -> None:
    namespace, function, kwargs = parse_plugin_command("stub.ping,key=dev1,enabled=true,count=3")
    assert namespace == "stub"
    assert function == "ping"
    assert kwargs == {"key": "dev1", "enabled": True, "count": 3}


def test_parse_plugin_command_rejects_bad_target() -> None:
    with pytest.raises(CommandInvokeError, match="namespace.function"):
        parse_plugin_command("ping")


def test_command_logical_name() -> None:
    assert command_logical_name("stub.ping,key=dev1") == "stub_ping"


def test_resolve_and_invoke_plugin_command(unit_runtime_context) -> None:
    calls: list[str] = []

    @command
    def ping(*, key: str = "") -> None:
        calls.append(key)

    module = types.ModuleType("stub_api")
    module.ping = ping
    module.__colosseum_domain__ = "stub"
    registry = unit_runtime_context.plugin_registry
    registry.register_namespace("stub", module)

    resolved = resolve_plugin_command("stub", "ping")
    assert resolved is ping
    invoke_plugin_commands(unit_runtime_context, ["stub.ping,key=abc"])
    assert calls == ["abc"]


def test_resolve_plugin_command_missing_namespace(unit_runtime_context, monkeypatch) -> None:
    _ = unit_runtime_context
    import colosseum.plugins.loader as loader

    monkeypatch.setattr(loader, "entry_points_for_group", lambda _group: [])
    with pytest.raises(CommandInvokeError, match="plugin namespace not found: nosuch"):
        resolve_plugin_command("nosuch", "fn")
