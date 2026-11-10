"""Import measurements and commands from a prior run directory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from colosseum.database import DatabaseManager
from colosseum.database.artifact_paths import relativize_imported_artifact

if TYPE_CHECKING:
    from pathlib import Path


def resolve_previous_run_dir(path: Path) -> Path:
    """Resolve a prior run directory, accepting optional ``-pass`` / ``-fail`` suffix."""
    from colosseum.paths import absolute_path

    resolved = absolute_path(path)
    if resolved.is_dir():
        return resolved
    raise FileNotFoundError(f"Previous output directory not found: {resolved}")


def resolve_previous_db(path: Path) -> Path:
    run_dir = resolve_previous_run_dir(path)
    db_path = run_dir / "execution.sqlite"
    if not db_path.is_file():
        raise FileNotFoundError(f"execution.sqlite not found in {run_dir}")
    return db_path


def import_evidence_from_previous(ctx: object, previous_dir: Path) -> None:
    """Copy measurements and commands from a prior run into the active database."""
    from colosseum.context import RuntimeContext

    if not isinstance(ctx, RuntimeContext):
        raise TypeError("ctx must be a RuntimeContext")
    if not ctx.db.is_initialized():
        raise RuntimeError("Database must be initialized before importing evidence")

    source_db = resolve_previous_db(previous_dir)
    source = DatabaseManager()
    source.open_readonly(source_db)
    try:
        for row in source.fetch_all_measurements():
            row.artifact_path = relativize_imported_artifact(row.artifact_path, source_db.parent)
            ctx.db.insert_measurement(row)
        for command in source.fetch_all_commands():
            ctx.db.insert_command(command)
    finally:
        source.close()

    ctx.db.insert_run_metadata("imported_from", str(source_db.parent))
