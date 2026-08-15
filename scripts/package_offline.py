#!/usr/bin/env python3
"""
Build an end-user offline install bundle (runtime wheels + smoke test + tarball).

Bundles contain ``colosseum-core[bench]`` (core + first-party plugins + hardware/SSH/GUI/plot)
for end-user bench hosts. Developers who need pytest, Sphinx, docgen, or PyVISA-sim install from
git clones (``requirements-dev.txt``), not from offline tarballs.

Usage:
  python scripts/package_offline.py
  python scripts/package_offline.py --skip-build   # reuse dist/*.tar.gz
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from ci.timing import ci_phase  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"
WHEELHOUSE = REPO_ROOT / "wheelhouse"
STAGING = REPO_ROOT / "offline-bundle"
SMOKE_DIR = REPO_ROOT / "scripts" / "offline_smoke"
SMOKE_SCRIPT = SMOKE_DIR / "run_sim.py"
SMOKE_CONFIG = SMOKE_DIR / "bench.sim.toml"
INSTALL_RST = REPO_ROOT / "docs" / "sphinx" / "source" / "guides" / "offline_install.rst"
INSTALL_SCRIPTS = REPO_ROOT / "scripts" / "offline_bundle"


def _read_version() -> str:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise RuntimeError("Could not read project version from pyproject.toml")
    return match.group(1)


def _platform_tag() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "windows":
        os_name = "windows"
    elif system == "darwin":
        os_name = "macos"
    else:
        os_name = "linux"
    return f"{os_name}-{machine}"


def _python_tag() -> str:
    target = os.environ.get("COLOSSEUM_OFFLINE_PYTHON_VERSION")
    if target:
        major_str, _, minor_str = target.partition(".")
        return f"py{major_str}{minor_str or '0'}"
    py_major, py_minor = sys.version_info[:2]
    return f"py{py_major}{py_minor}"


def _python_minor_label() -> str:
    tag = _python_tag()
    digits = (
        tag[2:] if tag.startswith("py") else f"{sys.version_info.major}{sys.version_info.minor}"
    )
    if len(digits) == 2:
        return f"{digits[0]}.{digits[1]}"
    return f"{digits[0]}.{digits[1:]}"


def _pip_download_args(*, only_binary: bool = True) -> list[str]:
    args: list[str] = []
    target = os.environ.get("COLOSSEUM_OFFLINE_PYTHON_VERSION")
    if target:
        args.extend(["--python-version", target])
        args.extend(["--platform", "manylinux2014_x86_64"])
        if only_binary:
            args.append("--only-binary=:all:")
    return args


def _offline_python_tuple() -> tuple[int, int] | None:
    target = os.environ.get("COLOSSEUM_OFFLINE_PYTHON_VERSION")
    if not target:
        return None
    major, _, minor = target.partition(".")
    return int(major), int(minor or "0")


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd or REPO_ROOT, check=True)


def _build_artifacts() -> tuple[Path, Path]:
    if shutil.which("python") is None:
        raise RuntimeError("python executable not found")
    _run([sys.executable, "-m", "pip", "install", "-q", "build"])
    if DIST_DIR.exists():
        for path in DIST_DIR.glob("colosseum*.*"):
            path.unlink()
    _run([sys.executable, "-m", "build", str(REPO_ROOT)])
    sdists = sorted(DIST_DIR.glob("colosseum_core-*.tar.gz")) + sorted(
        DIST_DIR.glob("colosseum-core-*.tar.gz")
    )
    wheels = sorted(DIST_DIR.glob("colosseum_core-*.whl")) + sorted(
        DIST_DIR.glob("colosseum-core-*.whl")
    )
    if not sdists or not wheels:
        raise RuntimeError(f"Expected sdist and wheel under {DIST_DIR}")
    return sdists[-1], wheels[-1]


def _download_wheels(wheel: Path) -> None:
    if WHEELHOUSE.exists():
        shutil.rmtree(WHEELHOUSE)
    WHEELHOUSE.mkdir(parents=True)
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--dest",
        str(WHEELHOUSE),
        *_pip_download_args(),
        f"{wheel}[bench]",
    ]
    _run(cmd)
    # Prefer locally built sibling plugin wheels when present.
    sibling_root = REPO_ROOT.parent
    for name in ("colosseum-shared", "colosseum-host", "colosseum-equipment"):
        sibling = sibling_root / name
        if not sibling.is_dir():
            continue
        _run([sys.executable, "-m", "build", str(sibling)])
        for built in (sibling / "dist").glob("*.whl"):
            shutil.copy2(built, WHEELHOUSE / built.name)
    offline_py = _offline_python_tuple()
    if offline_py is not None and offline_py < (3, 11):
        _run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--dest",
                str(WHEELHOUSE),
                *_pip_download_args(),
                "tomli",
            ]
        )


def _write_install_md(version: str, python_minor: str) -> str:
    return f"""# Colosseum offline install (v{version})

## Prerequisites

- Python {python_minor} (same minor as the ``pyXY`` tag in this bundle filename)
- ``python3-venv`` on Linux if creating a virtual environment

## Install (recommended)

**Windows:** Right-click the ``.tar.gz`` archive → **Extract All** (or **Extract**),
open the ``offline-bundle`` folder, then run one of the install scripts below from
that folder.

Linux / macOS: extract with ``tar xzf colosseum-*-offline-*.tar.gz``, ``cd offline-bundle``, then:

   ./install.sh

Windows PowerShell (from ``offline-bundle``)::

   .\\install.ps1

Windows Command Prompt (from ``offline-bundle``)::

   install.bat

Each script creates ``.venv`` in this directory, installs ``colosseum-core[bench]=={version}``
from ``wheels/``, and prints activation instructions.

## Manual install

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install --no-index --find-links=wheels "colosseum-core[bench]=={version}"
```

## Smoke test

```bash
colosseum run smoke/run_sim.py --config smoke/bench.sim.toml
```

Expected: exit code ``0`` and ``outputs/*/summary.txt`` with ``Overall result: PASS``.
"""


def _stage_bundle(version: str) -> Path:
    if STAGING.exists():
        shutil.rmtree(STAGING)
    wheels_dir = STAGING / "wheels"
    shutil.copytree(WHEELHOUSE, wheels_dir)

    smoke_dir = STAGING / "smoke"
    smoke_dir.mkdir(parents=True)
    shutil.copy2(SMOKE_CONFIG, smoke_dir / "bench.sim.toml")
    shutil.copy2(SMOKE_SCRIPT, smoke_dir / "run_sim.py")

    python_minor = _python_minor_label()
    (STAGING / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    (STAGING / "PYTHON_MINOR").write_text(f"{python_minor}\n", encoding="utf-8")

    for name in ("install.sh", "install.ps1", "install.bat"):
        src = INSTALL_SCRIPTS / name
        if not src.is_file():
            raise RuntimeError(f"Missing offline install script: {src}")
        dest = STAGING / name
        shutil.copy2(src, dest)
        if name.endswith(".sh"):
            dest.chmod(dest.stat().st_mode | 0o111)

    (STAGING / "INSTALL.md").write_text(_write_install_md(version, python_minor), encoding="utf-8")
    if INSTALL_RST.is_file():
        shutil.copy2(INSTALL_RST, STAGING / "offline_install.rst")
    return STAGING


def _create_tarball(version: str) -> Path:
    tag = f"{_platform_tag()}-{_python_tag()}"
    archive_name = f"colosseum-{version}-offline-{tag}.tar.gz"
    archive_path = REPO_ROOT / archive_name
    if archive_path.exists():
        archive_path.unlink()
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(STAGING, arcname="offline-bundle")
    return archive_path


def main(argv: list[str] | None = None) -> int:
    """Build an offline install tarball with wheels and smoke-test assets.

    :param argv: Optional argument vector (defaults to ``sys.argv[1:]``).
    :type argv: list[str] | None, optional

    :returns: Process exit code (``0`` on success, ``2`` when ``--skip-build`` finds no wheel).
    :rtype: int
    """
    parser = argparse.ArgumentParser(description="Build Colosseum offline install bundle")
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Reuse newest dist/colosseum-*.tar.gz instead of rebuilding",
    )
    args = parser.parse_args(argv)

    version = _read_version()
    if args.skip_build:
        wheels = sorted(DIST_DIR.glob("colosseum-*.whl"))
        if not wheels:
            print("No wheel in dist/; run without --skip-build", file=sys.stderr)
            return 2
        wheel = wheels[-1]
    else:
        with ci_phase("build_artifacts"):
            _, wheel = _build_artifacts()

    with ci_phase("download_wheels"):
        _download_wheels(wheel)
    with ci_phase("stage_bundle"):
        _stage_bundle(version)
    with ci_phase("create_tarball"):
        archive = _create_tarball(version)

    print(f"\nOffline bundle: {archive}")
    print(f"Staging dir:    {STAGING}")
    print(f"Wheels:         {WHEELHOUSE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
