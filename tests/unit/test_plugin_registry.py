"""U-PLG-01: plugin registry contracts."""

from __future__ import annotations

import types
from collections.abc import Callable

import pytest
from colosseum.config.sections import ConfigSectionSpec
from colosseum.plugins import loader
from colosseum.plugins.loader import ensure_plugins_loaded
from colosseum.plugins.registry import PluginRegistrationError, PluginRegistry


def test_shutdown_hooks_run_in_reverse_order() -> None:
    reg = PluginRegistry()
    order: list[int] = []
    reg.register_shutdown(lambda: order.append(1))
    reg.register_shutdown(lambda: order.append(2))
    reg.run_shutdown()
    assert order == [2, 1]


def test_duplicate_section_spec_fails_fast() -> None:
    reg = PluginRegistry()
    spec = ConfigSectionSpec("equipment.psu", "psu_id", ("driver",))
    reg.register_config_section(spec)
    with pytest.raises(PluginRegistrationError, match="already registered"):
        reg.register_config_section(spec)


def test_explicit_section_replacement() -> None:
    reg = PluginRegistry()
    original = ConfigSectionSpec("equipment.psu", "psu_id", ("driver",))
    replacement = ConfigSectionSpec("equipment.psu", "psu_id", ("resource",))
    reg.register_config_section(original)
    reg.replace_config_section(replacement)
    assert reg.config_section_specs() == [replacement]


def test_duplicate_namespace_fails_fast() -> None:
    reg = PluginRegistry()
    module = types.ModuleType("plugin")
    reg.register_namespace("equipment", module)
    with pytest.raises(PluginRegistrationError, match="already registered"):
        reg.register_namespace("equipment", module)


def test_explicit_namespace_replacement() -> None:
    reg = PluginRegistry()
    first = types.ModuleType("first")
    second = types.ModuleType("second")
    reg.register_namespace("equipment", first)
    reg.replace_namespace("equipment", second)
    assert reg.get_namespace("equipment") is second


def test_loader_loads_entry_points(monkeypatch: pytest.MonkeyPatch) -> None:
    class SampleEntryPoint:
        name = "equipment"

        def load(self) -> Callable[[PluginRegistry], None]:
            def register(registry: PluginRegistry) -> None:
                registry.register_namespace("equipment", types.ModuleType("equipment"))

            return register

    monkeypatch.setattr(loader, "entry_points_for_group", lambda _group: [SampleEntryPoint()])
    reg = PluginRegistry()
    ensure_plugins_loaded(reg)
    assert reg.has_namespace("equipment")


def test_loader_fails_fast_on_namespace_collision(monkeypatch: pytest.MonkeyPatch) -> None:
    class FirstEntryPoint:
        name = "first"

        def load(self) -> Callable[[PluginRegistry], None]:
            def register(registry: PluginRegistry) -> None:
                registry.register_namespace("equipment", types.ModuleType("first"))

            return register

    class CollidingEntryPoint:
        name = "vendor_equipment"

        def load(self) -> Callable[[PluginRegistry], None]:
            def register(registry: PluginRegistry) -> None:
                registry.register_namespace("equipment", types.ModuleType("vendor"))

            return register

    monkeypatch.setattr(
        loader,
        "entry_points_for_group",
        lambda _group: [FirstEntryPoint(), CollidingEntryPoint()],
    )
    reg = PluginRegistry()
    with pytest.raises(PluginRegistrationError, match="already registered"):
        ensure_plugins_loaded(reg)
