"""Freeze the active environment and pack the onedir bundle.

The bundle is the launcher plus the ``_internal`` directory PyInstaller writes
next to it. Windows packs that pair into ``dist/colosseum.zip``. Other
platforms pack it into ``dist/colosseum.tar.gz``.

Run with the same interpreter that has colosseum-core and its plugins installed:

    python -m colosseum.tools.build_executable
"""

from __future__ import annotations

import subprocess
import sys
import tarfile
import tempfile
import zipfile
from importlib import resources
from pathlib import Path
from typing import Literal

_APP_NAME = "colosseum"
ArchiveKind = Literal["zip", "gztar"]


def _launcher_name() -> str:
    if sys.platform == "win32":
        return f"{_APP_NAME}.exe"
    # Host platform makes one branch unreachable; keep both for the other OS.
    return _APP_NAME  # type: ignore[unused-ignore, unreachable]


def _default_archive_kind() -> ArchiveKind:
    if sys.platform == "win32":
        return "zip"
    # Host platform makes one branch unreachable; keep both for the other OS.
    return "gztar"  # type: ignore[unused-ignore, unreachable]


def archive_app(
    app_dir: Path,
    *,
    kind: ArchiveKind | None = None,
) -> Path:
    """Pack the launcher and ``_internal`` into a zip or gzipped tarball.

    Members sit under a ``colosseum/`` prefix, so extracting the archive
    recreates a directory you can run. Pass ``kind`` to force an archive type
    (unit tests); ``None`` selects zip on Windows and ``gztar`` elsewhere.
    """
    app_dir = app_dir.resolve()
    launcher = app_dir / _launcher_name()
    internal = app_dir / "_internal"
    if not launcher.is_file() or not internal.is_dir():
        raise SystemExit(f"Expected {launcher.name} and _internal inside {app_dir}")

    resolved_kind = _default_archive_kind() if kind is None else kind
    if resolved_kind == "zip":
        archive_path = app_dir.parent / f"{_APP_NAME}.zip"
        if archive_path.exists():
            archive_path.unlink()
        with zipfile.ZipFile(
            archive_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for path in app_dir.rglob("*"):
                if not path.is_file():
                    continue
                relative = path.relative_to(app_dir).as_posix()
                archive.write(path, f"{_APP_NAME}/{relative}")
        return archive_path

    archive_path = app_dir.parent / f"{_APP_NAME}.tar.gz"
    if archive_path.exists():
        archive_path.unlink()
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(app_dir, arcname=_APP_NAME)
    return archive_path


def main() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        raise SystemExit(
            "PyInstaller is not installed in this environment. "
            "Reinstall colosseum-core (it declares pyinstaller as a dependency).",
        ) from None

    entry_source = "from colosseum.runner.cli import main\nif __name__ == '__main__':\n    main()\n"
    cwd = Path.cwd()
    with (
        resources.as_file(resources.files("colosseum").joinpath("hooks")) as hook_dir,
        tempfile.TemporaryDirectory(prefix="colosseum-freeze-") as directory,
    ):
        work = Path(directory)
        entry = work / "entry.py"
        entry.write_text(entry_source, encoding="utf-8")
        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onedir",
            "--name",
            _APP_NAME,
            "--additional-hooks-dir",
            str(hook_dir),
            "--distpath",
            str(cwd / "dist"),
            "--workpath",
            str(cwd / "build"),
            "--specpath",
            str(work),
            str(entry),
        ]
        print("Running:", " ".join(command))
        completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    app_dir = cwd / "dist" / _APP_NAME
    print(f"Built {app_dir / _launcher_name()}")
    print(f"Archived {archive_app(app_dir)}")


if __name__ == "__main__":
    main()
