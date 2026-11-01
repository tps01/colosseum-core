"""absolute_path keeps drive-letter form; sqlite URI uses as_uri."""

from __future__ import annotations

from pathlib import Path

import pytest

from colosseum.database.artifact_paths import stored_artifact_path
from colosseum.database.manager import DatabaseManager
from colosseum.paths import absolute_path, sqlite_readonly_uri


def test_absolute_path_does_not_call_resolve(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def boom(self: Path) -> Path:
        raise AssertionError("resolve must not be used for user paths")

    monkeypatch.setattr(Path, "resolve", boom)
    target = tmp_path / "nested" / "file.txt"
    target.parent.mkdir()
    target.write_text("x", encoding="utf-8")
    got = absolute_path(target)
    assert got.is_absolute()
    assert got == target.absolute()


def test_sqlite_readonly_uri_matches_as_uri(tmp_path: Path) -> None:
    db = tmp_path / "execution.sqlite"
    DatabaseManager().initialize(db)
    uri = sqlite_readonly_uri(db)
    assert uri.startswith("file:")
    assert uri.endswith("?mode=ro")
    assert uri == absolute_path(db).as_uri() + "?mode=ro"
    manager = DatabaseManager()
    manager.open_readonly(db)
    assert manager.is_initialized()
    manager.close()


def test_stored_artifact_path_relativizes_without_resolve(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    def boom(self: Path) -> Path:
        raise AssertionError("resolve must not be used for artifact relativize")

    monkeypatch.setattr(Path, "resolve", boom)
    run_dir = tmp_path / "run"
    artifact = run_dir / "speca" / "trace.csv"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("a,b\n", encoding="utf-8")
    assert stored_artifact_path(artifact, run_dir) == "speca/trace.csv"
