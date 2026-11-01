"""Filesystem path helpers that keep mapped drive letters on Windows.

``Path.resolve()`` follows reparse points and often rewrites a mapped drive
(``B:\\…``) to a UNC path. User-facing config, output, and database paths should
stay in the form the operator supplied. Use :func:`absolute_path` instead of
``resolve`` for those cases. Package-relative ``Path(__file__).resolve()`` and
git probes may still use ``resolve``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]


def absolute_path(path: PathLike) -> Path:
    """Return an absolute path with ``.`` / ``..`` normalized, no symlink resolve.

    Uses :func:`os.path.abspath` so mapped drive letters are preserved on Windows.
    """
    # os.path.abspath (not Path.resolve) keeps mapped drive letters on Windows.
    return Path(os.path.abspath(str(Path(path).expanduser())))  # noqa: PTH100


def sqlite_readonly_uri(path: PathLike) -> str:
    """Build a SQLite URI for a read-only connection to ``path``."""
    return absolute_path(path).as_uri() + "?mode=ro"
