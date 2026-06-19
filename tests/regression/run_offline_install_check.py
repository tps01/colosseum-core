#!/usr/bin/env python3
"""R-OFFLINE-00: build end-user runtime bundle and install without network access."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKAGE_SCRIPT = REPO / "scripts" / "package_offline.py"
STAGING = REPO / "offline-bundle"
SMOKE_SCRIPT = STAGING / "smoke" / "run_sim.py"
SMOKE_CONFIG = STAGING / "smoke" / "bench.sim.toml"
WHEELS = STAGING / "wheels"


def _venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _install_from_bundle(bundle_root: Path) -> Path:
    """Run offline install scripts inside ``bundle_root`` and return venv python."""
    venv_dir = bundle_root / ".venv"
    if venv_dir.exists():
        shutil.rmtree(venv_dir)

    if sys.platform == "win32":
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(bundle_root / "install.ps1"),
            ],
            check=True,
            cwd=bundle_root,
        )
    else:
        subprocess.run(["sh", str(bundle_root / "install.sh")], check=True, cwd=bundle_root)

    venv_python = _venv_python(venv_dir)
    if not venv_python.is_file():
        raise RuntimeError(f"install script did not create venv at {venv_dir}")
    return venv_python


def _run_smoke(venv_python: Path, bundle_root: Path) -> int:
    smoke_script = bundle_root / "smoke" / "run_sim.py"
    smoke_config = bundle_root / "smoke" / "bench.sim.toml"

    help_proc = subprocess.run(
        [str(venv_python), "-m", "colosseum.runner.cli", "--help"],
        cwd=bundle_root,
    )
    if help_proc.returncode != 0:
        print("OFFLINE FAIL: colosseum --help failed", file=sys.stderr)
        return help_proc.returncode

    smoke_proc = subprocess.run(
        [
            str(venv_python),
            "-m",
            "colosseum.runner.cli",
            "run",
            str(smoke_script),
            "--config",
            str(smoke_config),
        ],
        cwd=bundle_root,
    )
    if smoke_proc.returncode != 0:
        print("OFFLINE FAIL: smoke test returned non-zero", file=sys.stderr)
        return smoke_proc.returncode
    return 0


def _find_offline_tarball() -> Path:
    archives = sorted(REPO.glob("colosseum-*-offline-*.tar.gz"))
    if not archives:
        raise FileNotFoundError("no colosseum-*-offline-*.tar.gz found in repository root")
    return archives[-1]


def _extract_tarball(archive: Path, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(dest)
    bundle_root = dest / "offline-bundle"
    if not bundle_root.is_dir():
        raise RuntimeError(f"expected offline-bundle/ in {archive}")
    return bundle_root


def _verify_staging_layout() -> int:
    for path in (WHEELS, SMOKE_SCRIPT, STAGING / "install.sh", STAGING / "install.ps1"):
        if not path.exists():
            print(f"OFFLINE FAIL: offline-bundle staging incomplete ({path})", file=sys.stderr)
            return 1
    return 0


def _test_staging_install() -> int:
    try:
        venv_python = _install_from_bundle(STAGING)
        return _run_smoke(venv_python, STAGING)
    finally:
        shutil.rmtree(STAGING / ".venv", ignore_errors=True)


def _test_tarball_install(archive: Path) -> int:
    with tempfile.TemporaryDirectory(prefix="colosseum-offline-tarball-") as tmp:
        extract_root = Path(tmp)
        bundle_root = _extract_tarball(archive, extract_root)
        for path in (
            bundle_root / "wheels",
            bundle_root / "smoke" / "run_sim.py",
            bundle_root / "install.sh",
            bundle_root / "install.ps1",
        ):
            if not path.exists():
                print(f"OFFLINE FAIL: tarball extract incomplete ({path})", file=sys.stderr)
                return 1

        try:
            venv_python = _install_from_bundle(bundle_root)
            return _run_smoke(venv_python, bundle_root)
        finally:
            shutil.rmtree(bundle_root / ".venv", ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for R-OFFLINE-00 host offline bundle regression.

    :param argv: Optional argument vector (defaults to ``sys.argv[1:]``).
    :type argv: list[str] | None, optional

    :returns: Process exit code (``0`` on success).
    :rtype: int
    """
    parser = argparse.ArgumentParser(description="Verify Colosseum offline bundle install")
    parser.add_argument(
        "--skip-tarball",
        action="store_true",
        help="Only test staging-dir install (skip release .tar.gz extract path)",
    )
    args = parser.parse_args(argv)

    if not PACKAGE_SCRIPT.is_file():
        print(f"Missing packaging script: {PACKAGE_SCRIPT}", file=sys.stderr)
        return 2

    proc = subprocess.run([sys.executable, str(PACKAGE_SCRIPT)], cwd=REPO, timeout=900)
    if proc.returncode != 0:
        print("OFFLINE FAIL: package_offline.py returned non-zero", file=sys.stderr)
        return proc.returncode

    code = _verify_staging_layout()
    if code != 0:
        return code

    code = _test_staging_install()
    if code != 0:
        return code
    print("OFFLINE PASS: staging-dir install and smoke test succeeded")

    if args.skip_tarball:
        return 0

    try:
        archive = _find_offline_tarball()
    except FileNotFoundError as exc:
        print(f"OFFLINE FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"OFFLINE: testing tarball extract path ({archive.name})")
    code = _test_tarball_install(archive)
    if code != 0:
        return code

    print("OFFLINE PASS: tarball extract, install, and smoke test succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
