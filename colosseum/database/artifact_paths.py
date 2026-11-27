"""Persist and resolve measurement artifact paths across run renames and imports."""

from __future__ import annotations

import os
import re
from pathlib import Path

from colosseum.paths import absolute_path, is_link_entry

_RESULT_SUFFIX = re.compile(r"-(?:pass|fail|incomplete)(?:_[1-9][0-9]*)?$")


def _through_link(path: Path, *, require_target: bool = False) -> bool:
    linked = False
    for part in (*reversed(path.parents), path):
        try:
            entry = part.lstat()
        except FileNotFoundError:
            break
        if is_link_entry(entry):
            if not require_target:
                return True
            part.stat()
            linked = True
    return linked


def stored_artifact_path(path: Path | str, output_dir: Path | None) -> str:
    """Return the string to store in ``measurements.artifact_path``.

    Paths inside ``output_dir`` are stored relative to that directory (POSIX
    separators) so a later ``-pass`` / ``-fail`` rename still finds them.
    Paths outside the run directory stay absolute.
    """
    candidate = Path(path)
    if output_dir is None:
        return candidate.as_posix() if not candidate.is_absolute() else str(candidate)
    root = absolute_path(output_dir)
    candidate = absolute_path(root / candidate)
    # A link to the entire run directory is part of the run's address. Inspect
    # the actual target for containment, keeping ordinary external paths as given.
    linked = _through_link(candidate, require_target=True)
    if ".." in candidate.parts and not candidate.exists():
        return str(candidate)
    target = Path(os.path.realpath(candidate))
    real_root = Path(os.path.realpath(root))
    try:
        return target.relative_to(real_root).as_posix()
    except ValueError:
        return str(target if linked or ".." in candidate.parts else candidate)


def resolve_stored_artifact(
    stored: str,
    *,
    run_dir: Path,
    import_origin: Path | None = None,
) -> Path:
    """Resolve a stored artifact path against the owning run, then an import origin.

    Absolute paths that still exist are returned as-is. Absolute paths that
    disappeared because the run directory was renamed are rebased under the
    corresponding result directory.
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
    resolved = resolve_stored_artifact(text, run_dir=source_run)
    if _through_link(resolved):
        # Imported evidence stays with the source even if the destination has
        # a file at the same relative path.
        return str(Path(os.path.realpath(resolved))) if resolved.is_file() else str(resolved)
    if Path(text).is_absolute() and resolved.is_file():
        return stored_artifact_path(resolved, source_run)
    return text if Path(text).is_absolute() else text.replace("\\", "/")


def _rebase_missing_absolute(stored: Path, run_dir: Path) -> Path | None:
    if not _RESULT_SUFFIX.search(run_dir.name):
        return None
    base = _RESULT_SUFFIX.sub("", run_dir.name)
    for ancestor in stored.parents:
        if ancestor.parent != run_dir.parent or ancestor == run_dir:
            continue
        if _RESULT_SUFFIX.sub("", ancestor.name) == base:
            candidate = run_dir / stored.relative_to(ancestor)
            return candidate if candidate.is_file() else None
    return None
