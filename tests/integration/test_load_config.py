"""I-CFG: standalone configuration and plugin namespaces."""

from __future__ import annotations

import colosseum as col
import types

from colosseum.config import load_config
from colosseum.context import init_context


def test_core_config_loads_without_plugins(core_config, isolated_cwd) -> None:
    store = load_config(core_config)
    assert store.raw() == {}
    assert col.config.is_loaded()


def test_lazy_namespace_resolves_registered_plugin(core_config, isolated_cwd) -> None:
    ctx = init_context(test_case_name="plugin")
    module = types.ModuleType("acme_api")
    module.ping = lambda: "pong"  # type: ignore[attr-defined]
    ctx.plugin_registry.register_namespace("acme", module)
    ctx.plugin_registry.loaded = True
    load_config(core_config)
    assert col.acme.ping() == "pong"


def test_unregistered_sections_remain_available_as_raw_config(
    isolated_cwd, tmp_path
) -> None:
    path = tmp_path / "settings.toml"
    path.write_text("[runtime]\nlabel = \"bench-a\"\n", encoding="utf-8")
    store = load_config(path)
    assert store.get_section("runtime.label") == "bench-a"
