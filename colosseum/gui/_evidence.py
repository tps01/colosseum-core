"""Artifact links for one evidence row. Associations stay explicit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from colosseum.database.artifact_paths import resolve_stored_artifact

if TYPE_CHECKING:
    from ._results import EvidenceRow

_TEXT_SUFFIXES = frozenset({".txt", ".log", ".csv", ".json", ".md", ".toml", ".yaml", ".yml"})
_IMAGE_SUFFIXES = frozenset({".png", ".gif", ".ppm", ".pgm"})
_PREVIEW_CHARS = 8000


@dataclass(frozen=True)
class ArtifactLink:
    stored: str
    path: Path
    exists: bool
    associated: bool


def links_for_row(
    row: EvidenceRow,
    rows: list[EvidenceRow],
    *,
    run_dir: Path,
    import_origin: str | None,
) -> list[ArtifactLink]:
    """Return artifacts that belong to this row.

    A verification uses a measurement artifact only when exactly one measurement
    with the same domain, command, and key stored a path.
    """
    origin = _origin_path(import_origin)
    stored_paths: list[str] = []
    if row.artifact_stored:
        stored_paths.append(row.artifact_stored)
    elif row.kind == "verification" and row.key:
        matches = [
            other.artifact_stored
            for other in rows
            if other.kind == "measurement"
            and other.domain == row.domain
            and other.command == row.command
            and other.key == row.key
            and other.artifact_stored
        ]
        if len(matches) == 1:
            stored_paths.append(matches[0])
    return [
        _link(stored, run_dir=run_dir, origin=origin, associated=True) for stored in stored_paths
    ]


def unassociated_files(
    run_dir: Path, linked: list[ArtifactLink], *, limit: int = 20,
) -> list[ArtifactLink]:
    """Files sitting in the run folder that are not tied to the selected row."""
    known = {item.path.resolve() for item in linked if item.exists}
    found: list[ArtifactLink] = []
    if not run_dir.is_dir():
        return found
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file() or path.name in {"execution.sqlite", "summary.json", "debug.log"}:
            continue
        if path.suffix.lower() not in _TEXT_SUFFIXES | _IMAGE_SUFFIXES:
            continue
        if path.resolve() in known:
            continue
        found.append(ArtifactLink(stored=path.name, path=path, exists=True, associated=False))
        if len(found) >= limit:
            break
    return found


def preview_text(path: Path) -> str | None:
    if path.suffix.lower() not in _TEXT_SUFFIXES or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:_PREVIEW_CHARS]
    except OSError as exc:
        return f"Cannot read {path.name}: {exc}"


def _link(stored: str, *, run_dir: Path, origin: Path | None, associated: bool) -> ArtifactLink:
    path = resolve_stored_artifact(stored, run_dir=run_dir, import_origin=origin)
    return ArtifactLink(stored=stored, path=path, exists=path.is_file(), associated=associated)


def _origin_path(import_origin: str | None) -> Path | None:
    if not import_origin:
        return None
    return Path(import_origin)
