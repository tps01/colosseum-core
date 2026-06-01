#!/usr/bin/env python3
"""
Build an offline install bundle (wheelhouse + smoke files + tarball).

Usage:
  python scripts/package_offline.py
  python scripts/package_offline.py --include-dev
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

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"
WHEELHOUSE = REPO_ROOT / "wheelhouse"
STAGING = REPO_ROOT / "offline-bundle"
SMOKE_DIR = REPO_ROOT / "scripts" / "offline_smoke"
SMOKE_SCRIPT = SMOKE_DIR / "run_sim.py"
SMOKE_CONFIG = SMOKE_DIR / "bench.sim.toml"
INSTALL_RST = REPO_ROOT / "docs" / "sphinx" / "source" / "guides" / "offline_install.rst"


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
        major, _, minor = target.partition(".")
        return f"py{major}{minor or '0'}"
    major, minor = sys.version_info[:2]
    return f"py{major}{minor}"


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
        for path in DIST_DIR.glob("colosseum-*.*"):
            path.unlink()
    _run([sys.executable, "-m", "build", str(REPO_ROOT)])
    sdists = sorted(DIST_DIR.glob("colosseum-*.tar.gz"))
    wheels = sorted(DIST_DIR.glob("colosseum-*.whl"))
    if not sdists or not wheels:
        raise RuntimeError(f"Expected sdist and wheel under {DIST_DIR}")
    return sdists[-1], wheels[-1]


def _download_wheels(wheel: Path, *, include_dev: bool) -> None:
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
        str(wheel),
    ]
    _run(cmd)
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
    if include_dev:
        dev_req = REPO_ROOT / "requirements-dev.txt"
        if not dev_req.is_file():
            raise RuntimeError(f"Missing dev requirements: {dev_req}")
        _run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--dest",
                str(WHEELHOUSE),
                *_pip_download_args(),
                "-r",
                str(dev_req),
            ]
        )


def _write_install_md(version: str, *, include_dev: bool) -> str:
    dev_note = (
        "\nDev tools (pytest, Sphinx, mutation) are included in ``wheels/``.\n"
        if include_dev
        else ""
    )
    return f"""# Colosseum offline install (v{version})

## Prerequisites

- Python {sys.version_info.major}.{sys.version_info.minor} (same as the machine that built this bundle)
- ``python3-venv`` on Linux if creating a virtual environment

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install --no-index --find-links=wheels colosseum=={version}
```

{dev_note}
## Smoke test

```bash
colosseum run smoke/run_sim.py --config smoke/bench.sim.toml
```

Expected: exit code ``0`` and ``outputs/*/summary.txt`` with ``Overall result: PASS``.
"""


def _stage_bundle(version: str, *, include_dev: bool) -> Path:
    if STAGING.exists():
        shutil.rmtree(STAGING)
    wheels_dir = STAGING / "wheels"
    shutil.copytree(WHEELHOUSE, wheels_dir)

    smoke_dir = STAGING / "smoke"
    smoke_dir.mkdir(parents=True)
    shutil.copy2(SMOKE_CONFIG, smoke_dir / "bench.sim.toml")
    shutil.copy2(SMOKE_SCRIPT, smoke_dir / "run_sim.py")

    (STAGING / "INSTALL.md").write_text(
        _write_install_md(version, include_dev=include_dev),
        encoding="utf-8",
    )
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
    parser = argparse.ArgumentParser(description="Build Colosseum offline install bundle")
    parser.add_argument(
        "--include-dev",
        action="store_true",
        help="Also download wheels for requirements-dev.txt",
    )
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
        _, wheel = _build_artifacts()

    _download_wheels(wheel, include_dev=args.include_dev)
    _stage_bundle(version, include_dev=args.include_dev)
    archive = _create_tarball(version)

    print(f"\nOffline bundle: {archive}")
    print(f"Staging dir:    {STAGING}")
    print(f"Wheels:         {WHEELHOUSE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
