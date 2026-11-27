"""Filesystem path helpers that keep mapped drive letters on Windows.

``Path.resolve()`` follows reparse points and often rewrites a mapped drive
(``B:\\…``) to a UNC path. User-facing config, output, and database paths should
stay in the form the operator supplied. Use :func:`absolute_path` instead of
``resolve`` for those cases. Package-relative ``Path(__file__).resolve()`` and
git probes may still use ``resolve``.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]


def absolute_path(path: PathLike) -> Path:
    """Anchor a path without resolving links or changing its drive spelling."""
    expanded = Path(path).expanduser()
    if os.name == "nt":
        # Win32 applies lexical normalization before following reparse points.
        return Path(os.path.abspath(expanded))  # noqa: PTH100
    anchored = expanded if expanded.is_absolute() else Path.cwd() / expanded
    if ".." not in anchored.parts:
        return anchored
    current = Path(anchored.anchor)
    for component in anchored.parts[1:]:
        if component != "..":
            current /= component
            continue
        try:
            # Collapsing a parent step is safe only after a real directory.
            if not stat.S_ISDIR(current.lstat().st_mode):
                return anchored
            (current / "..").stat()
        except OSError:
            return anchored
        current = current.parent
    return current


def link_target(path: Path) -> Path:
    """Follow file links while retaining directory aliases in the resulting path."""
    current = absolute_path(path)
    if current.is_symlink():
        current.stat()  # Let the OS reject broken links and cycles.
    seen: set[Path] = set()
    while current.is_symlink():
        if current in seen:
            raise OSError(f"Symbolic link cycle: {path}")
        seen.add(current)
        target = current.readlink()
        if os.name == "nt" and target.drive.startswith("\\\\?\\") and len(target.drive) == 6:
            target = Path(str(target)[4:])
        current = absolute_path(current.parent / target)
    return current


def is_link_entry(info: os.stat_result) -> bool:
    """Recognize symbolic links and Windows directory junctions from lstat."""
    return stat.S_ISLNK(info.st_mode) or (
        sys.platform == "win32" and getattr(info, "st_reparse_tag", 0) == stat.IO_REPARSE_TAG_MOUNT_POINT
    )


def sqlite_readonly_uri(path: PathLike) -> str:
    """Build a SQLite URI for a read-only connection to ``path``."""
    return absolute_path(path).as_uri() + "?mode=ro"
