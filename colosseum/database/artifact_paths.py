"""Persist and resolve measurement artifact paths across run renames and imports."""

from __future__ import annotations

from pathlib import Path

from colosseum.paths import absolute_path


def stored_artifact_path(path: Path | str, output_dir: Path | None) -> str:
    """Return the string to store in ``measurements.artifact_path``.

    Paths inside ``output_dir`` are stored relative to that directory (POSIX
    separators) so a later ``-pass`` / ``-fail`` rename still finds them.
    Paths outside the run directory stay absolute.
    """
    candidate = Path(path)
    if output_dir is None:
        return candidate.as_posix() if not candidate.is_absolute() else str(candidate)
    if not candidate.is_absolute():
        return candidate.as_posix()
    try:
        relative = absolute_path(candidate).relative_to(absolute_path(output_dir))
    except ValueError:
        return str(absolute_path(candidate))
    return relative.as_posix()


def resolve_stored_artifact(
    stored: str,
    *,
    run_dir: Path,
    import_origin: Path | None = None,
) -> Path:
    """Resolve a stored artifact path against the owning run, then an import origin.

    Absolute paths that still exist are returned as-is. Absolute paths that
    disappeared because the run directory was renamed are rebased by matching
    a suffix under ``run_dir`` (and ``import_origin`` when set).
    """
    text = stored.replace("\\", "/")
    candidate = Path(stored)
    if candidate.is_absolute():
        if candidate.is_file():
            return candidate
        for root in (run_dir, import_origin):
            if root is None:
                continue
            rebased = _rebase_missing_absolute(candidate, root)
            if rebased is not None:
                return rebased
        return candidate

    relative = Path(text)
    for root in (run_dir, import_origin):
        if root is None:
            continue
        joined = absolute_path(root / relative)
        if joined.is_file():
            return joined
    return absolute_path(run_dir / relative)


def relativize_imported_artifact(stored: str | None, source_run: Path) -> str | None:
    """Store an imported artifact relative to ``source_run`` when it lives there."""
    if stored is None or stored == "":
        return None
    text = str(stored)
    path = Path(text)
    if not path.is_absolute():
        return text.replace("\\", "/")
    resolved = resolve_stored_artifact(text, run_dir=source_run)
    try:
        return absolute_path(resolved).relative_to(absolute_path(source_run)).as_posix()
    except ValueError:
        if resolved.is_file():
            return str(resolved)
        return text


def _rebase_missing_absolute(stored: Path, run_dir: Path) -> Path | None:
    parts = stored.parts
    # Skip the drive/root component; try longest meaningful suffix first.
    for start in range(1, len(parts)):
        suffix = Path(*parts[start:])
        candidate = absolute_path(run_dir / suffix)
        if candidate.is_file():
            return candidate
    return None
