"""Public path helpers for Colosseum plugins.

Plugins (``gui``, ``host``, ``equipment``, ``messaging``, ``shared``) import
from this module rather than ``colosseum.runner.runtime``. Keep the re-exports
stable; treat this as the supported facade for allocating and resolving run
output directories.
"""

from .runtime import (
    allocate_run_directory,
    ensure_output_dir,
    ensure_runtime_ready,
    rename_run_directory_for_result,
    sanitize_logical_name,
)

__all__ = [
    "allocate_run_directory",
    "ensure_output_dir",
    "ensure_runtime_ready",
    "rename_run_directory_for_result",
    "sanitize_logical_name",
]
