"""Unit tests for shared decorator helpers."""

from __future__ import annotations

import pytest
from colosseum.decorators._common import ensure_runtime_context, resolve_command, resolve_domain


def test_resolve_domain_io_module_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    def sample() -> None:
        return None

    monkeypatch.setattr(sample, "__module__", "colosseum_equipment.io.api.dio")
    assert resolve_domain(sample) == "equipment"


def test_resolve_command_qualifies_first_party_public_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def sample() -> None:
        return None

    monkeypatch.setattr(sample, "__module__", "colosseum_equipment.api.dmm")
    monkeypatch.setattr(sample, "__name__", "measure_voltage")
    assert resolve_command(sample) == "dmm.measure_voltage"

    monkeypatch.setattr(sample, "__module__", "colosseum_equipment.io.api.dio")
    monkeypatch.setattr(sample, "__name__", "read_port")
    assert resolve_command(sample) == "io.dio.read_port"

    monkeypatch.setattr(sample, "__module__", "colosseum_shared.ssh.api")
    monkeypatch.setattr(sample, "__name__", "measure_stdout")
    assert resolve_command(sample) == "ssh.measure_stdout"


def test_ensure_runtime_context_requires_initialized_context() -> None:
    import colosseum.context as context_module

    context_module._ACTIVE_CONTEXT = None
    with pytest.raises(RuntimeError, match="Runtime is not initialized"):
        ensure_runtime_context()
