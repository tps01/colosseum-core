"""Lazy plugin API module proxy."""

from __future__ import annotations

import sys
import types

from colosseum.plugins.lazy import LazyModuleProxy, lazy_module


def test_lazy_module_imports_on_first_attribute_access(monkeypatch) -> None:
    calls: list[str] = []
    real = types.ModuleType("colosseum_test_lazy_target")
    real.marker = "loaded"  # type: ignore[attr-defined]

    def fake_import(name: str) -> types.ModuleType:
        calls.append(name)
        assert name == "colosseum_test_lazy_target"
        return real

    monkeypatch.setattr("importlib.import_module", fake_import)
    proxy = lazy_module("colosseum_test_lazy_target", name="col.test.lazy")
    assert isinstance(proxy, LazyModuleProxy)
    assert calls == []
    assert proxy.marker == "loaded"
    assert calls == ["colosseum_test_lazy_target"]
    assert proxy.marker == "loaded"
    assert calls == ["colosseum_test_lazy_target"]


def test_lazy_module_dir_loads_target(monkeypatch) -> None:
    real = types.ModuleType("colosseum_test_lazy_dir")
    real.value = 1  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "colosseum_test_lazy_dir", real)
    proxy = lazy_module("colosseum_test_lazy_dir")
    assert "value" in dir(proxy)
