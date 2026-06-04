"""Runtime/package version consistency."""

from __future__ import annotations

from pathlib import Path

import colosseum

try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


def test_runtime_version_matches_pyproject(repo_root: Path) -> None:
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))

    assert colosseum.__version__ == pyproject["project"]["version"]
