"""Entry point discovery via compat shim."""

from __future__ import annotations

from colosseum.compat.entry_points import entry_points_for_group


def test_colosseum_plugins_entry_points_discoverable() -> None:
    eps = entry_points_for_group("colosseum.plugins")
    names = {getattr(ep, "name", None) for ep in eps}
    assert "equipment" in names
    assert "shared" in names


def test_colosseum_docgen_entry_points_discoverable() -> None:
    eps = entry_points_for_group("colosseum.docgen")
    names = {getattr(ep, "name", None) for ep in eps}
    assert "colosseum" in names
    assert "equipment" in names
