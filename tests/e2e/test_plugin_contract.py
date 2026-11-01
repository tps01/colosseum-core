"""E2E-PLG: real setuptools entry-point discovery and plugin registration."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.e2e_specifications import run_python_script
from tests.support.helpers import CORE_CONFIG, FIXTURES, REPO_ROOT

PROBE_ROOT = FIXTURES / "plugins" / "colosseum_contract_probe"
BROKEN_ROOT = FIXTURES / "plugins" / "colosseum_contract_broken"
PROBE_DIST = "colosseum-contract-probe"
BROKEN_DIST = "colosseum-contract-broken"
PROBE_SMOKE = FIXTURES / "scripts" / "contract_probe_smoke.py"
BROKEN_LOAD = FIXTURES / "scripts" / "contract_broken_load.py"
PROBE_CONFIG = PROBE_ROOT / "configs" / "contract_probe.toml"


def _pip(*args: str) -> None:
    subprocess.check_call(
        [sys.executable, "-m", "pip", *args],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def _pip_uninstall(dist_name: str) -> None:
    subprocess.call(
        [sys.executable, "-m", "pip", "uninstall", "-y", dist_name],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _pip_install_editable(root: Path) -> None:
    _pip("install", "-e", str(root), "--no-deps", "-q")


def _dist_installed(dist_name: str) -> bool:
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "show", dist_name],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


@pytest.fixture
def installed_probe_only() -> Path:
    _pip_uninstall(BROKEN_DIST)
    _pip_install_editable(PROBE_ROOT)
    assert _dist_installed(PROBE_DIST)
    try:
        yield PROBE_ROOT
    finally:
        _pip_uninstall(PROBE_DIST)
        assert not _dist_installed(PROBE_DIST)


@pytest.fixture
def installed_broken_only() -> Path:
    _pip_uninstall(PROBE_DIST)
    _pip_install_editable(BROKEN_ROOT)
    assert _dist_installed(BROKEN_DIST)
    try:
        yield BROKEN_ROOT
    finally:
        _pip_uninstall(BROKEN_DIST)
        assert not _dist_installed(BROKEN_DIST)


@pytest.mark.requirement("E2E-PLG-01")
def test_installed_plugin_is_discovered_and_attached(
    installed_probe_only: Path,
    isolated_cwd: Path,
    subprocess_env: dict[str, str],
) -> None:
    """Editable install → EP discovery → col.contract_probe + config + measurement."""
    _ = installed_probe_only
    env = dict(subprocess_env)
    env["CONTRACT_PROBE_CONFIG"] = str(PROBE_CONFIG)
    proc = run_python_script(PROBE_SMOKE, isolated_cwd, env)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    marker = "CONTRACT_PROBE_OK:"
    lines = [line for line in proc.stdout.splitlines() if line.startswith(marker)]
    assert lines, proc.stdout
    payload = json.loads(lines[-1][len(marker) :])
    assert "contract_probe" in payload["ep_names"]
    assert payload["serial"] == "PROBE-1"
    assert payload["measurement"] == "token-ok"


@pytest.mark.requirement("E2E-PLG-02")
def test_broken_plugin_register_fails_fast(
    installed_broken_only: Path,
    isolated_cwd: Path,
    subprocess_env: dict[str, str],
) -> None:
    """Broken register() surfaces PluginRegistrationError with the EP name."""
    _ = installed_broken_only
    env = dict(subprocess_env)
    env["CONTRACT_BROKEN_CONFIG"] = str(CORE_CONFIG)
    proc = run_python_script(BROKEN_LOAD, isolated_cwd, env)
    combined = (proc.stdout or "") + (proc.stderr or "")
    assert proc.returncode == 2, combined
    assert "PluginRegistrationError" in combined
    assert "contract_broken" in combined

    _pip_uninstall(BROKEN_DIST)
    assert not _dist_installed(BROKEN_DIST)
    clean = subprocess.run(
        [sys.executable, "-c", "import colosseum as col; print('ok', col.__version__)"],
        cwd=isolated_cwd,
        env=subprocess_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert clean.returncode == 0, clean.stderr
    assert "ok" in clean.stdout
