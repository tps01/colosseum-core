"""E2E-PLG: real setuptools entry-point discovery and plugin registration.

The disposable interpreter is a normal virtual environment. Pip and setuptools
come from ensurepip, and only the import-time libraries the runtime needs are
copied in. It is not an offline-installer proof: core is installed with
``--no-deps``.
"""

from __future__ import annotations

import json
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

import pytest

from tests.support.e2e_specifications import run_python_script
from tests.support.helpers import CORE_CONFIG, FIXTURES, REPO_ROOT, query_db

PROBE_ROOT = FIXTURES / "plugins" / "colosseum_contract_probe"
BROKEN_ROOT = FIXTURES / "plugins" / "colosseum_contract_broken"
BROKEN_DIST = "colosseum-contract-broken"
PROBE_SMOKE = FIXTURES / "scripts" / "contract_probe_smoke.py"
BROKEN_LOAD = FIXTURES / "scripts" / "contract_broken_load.py"
PROBE_COMMAND = FIXTURES / "scripts" / "contract_probe_command.py"
PROBE_CONFIG = PROBE_ROOT / "configs" / "contract_probe.toml"


def _pip(python: Path, *args: str) -> None:
    env = os.environ.copy()
    root = str(python.parent.parent.parent)
    env.update(TEMP=root, TMP=root)
    env.pop("PYTHONPATH", None)
    env["PYTHONNOUSERSITE"] = "1"
    proc = subprocess.run(
        [str(python), "-m", "pip", "--no-cache-dir", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
        check=False,
    )
    detail = (proc.stderr or proc.stdout or "").strip()
    assert proc.returncode == 0, detail


@pytest.fixture(scope="session")
def plugin_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Prepare tooling once; individual tests receive separate copies."""
    directory = tmp_path_factory.mktemp("plugin-template")
    venv.EnvBuilder(with_pip=True).create(directory)
    python = directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    # Keep the build backend out of host site-packages and plugin metadata.
    _pip(python, "install", "setuptools>=68")
    packages = directory / (
        "Lib/site-packages"
        if os.name == "nt"
        else f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
    )
    # Only core's import-time dependencies; never inherit installed plugin metadata.
    for name in ("yaml", "tomli", "typing_extensions"):
        spec = importlib.util.find_spec(name)
        if spec is not None and spec.origin:
            source = Path(spec.origin)
            if spec.submodule_search_locations:
                shutil.copytree(source.parent, packages / name, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(source, packages / source.name)
    return directory


@pytest.fixture
def plugin_python(tmp_path: Path, plugin_template: Path) -> Path:
    """Install fixture plugins only in a disposable interpreter, even if setup fails."""
    with tempfile.TemporaryDirectory(dir=tmp_path) as directory:
        shutil.copytree(plugin_template, directory, dirs_exist_ok=True)
        yield Path(directory) / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


@pytest.fixture(params=["editable", "wheel"])
def installed_probe_only(plugin_python: Path, request) -> Path:
    if request.param == "wheel":
        wheels = plugin_python.parent.parent / "wheels"
        _pip(
            plugin_python,
            "wheel",
            str(REPO_ROOT),
            "--wheel-dir",
            str(wheels),
            "--no-deps",
            "--no-build-isolation",
            "--no-index",
            "-q",
        )
        _pip(
            plugin_python,
            "install",
            str(next(wheels.glob("colosseum_core-*.whl"))),
            "--no-deps",
            "--no-index",
            "-q",
        )
    else:
        _pip(
            plugin_python,
            "install",
            "-e",
            str(REPO_ROOT),
            "--no-deps",
            "--no-build-isolation",
            "--no-index",
            "-q",
        )
    _pip(
        plugin_python,
        "install",
        "-e",
        str(PROBE_ROOT),
        "--no-deps",
        "--no-build-isolation",
        "--no-index",
        "-q",
    )
    return plugin_python


@pytest.fixture
def installed_broken_only(plugin_python: Path) -> Path:
    _pip(
        plugin_python,
        "install",
        "-e",
        str(BROKEN_ROOT),
        "--no-deps",
        "--no-build-isolation",
        "--no-index",
        "-q",
    )
    return plugin_python


@pytest.mark.requirement("E2E-PLG-01")
@pytest.mark.requirement("E2E-RUN-11")
def test_installed_plugin_is_discovered_and_attached(
    installed_probe_only: Path,
    isolated_cwd: Path,
    subprocess_env: dict[str, str],
) -> None:
    """Editable install → EP discovery → col.contract_probe + config + measurement."""
    _ = installed_probe_only
    env = dict(subprocess_env)
    env.pop("PYTHONPATH", None)
    env["CONTRACT_PROBE_CONFIG"] = str(PROBE_CONFIG)
    proc = run_python_script(PROBE_SMOKE, isolated_cwd, env, python=installed_probe_only)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "CONTRACT_PROBE_REPORT_OK" in proc.stdout
    marker = "CONTRACT_PROBE_OK:"
    lines = [line for line in proc.stdout.splitlines() if line.startswith(marker)]
    assert lines, proc.stdout
    payload = json.loads(lines[-1][len(marker) :])
    assert "contract_probe" in payload["ep_names"]
    assert payload["serial"] == "PROBE-1"
    assert payload["measurement"] == "token-ok"

    before = set((isolated_cwd / "outputs").iterdir())
    command = subprocess.run(
        [
            str(installed_probe_only),
            "-m",
            "colosseum.runner.cli",
            "run",
            str(PROBE_COMMAND),
            "--config",
            str(PROBE_CONFIG),
        ],
        cwd=isolated_cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert command.returncode == 0, command.stderr or command.stdout
    created = set((isolated_cwd / "outputs").iterdir()) - before
    assert len(created) == 1
    rows = query_db(created.pop(), "SELECT domain, command, status FROM commands")
    assert rows == [("contract_probe", "ping", "PASS")]


@pytest.mark.skipif(
    not os.environ.get("COLOSSEUM_FROZEN_EXECUTABLE"),
    reason="Set COLOSSEUM_FROZEN_EXECUTABLE to a real bundle with the probe plugin",
)
def test_real_frozen_plugin_contract(isolated_cwd, subprocess_env):
    env = dict(subprocess_env)
    env.pop("PYTHONPATH", None)
    env["CONTRACT_PROBE_CONFIG"] = str(PROBE_CONFIG)
    proc = subprocess.run(
        [
            os.environ["COLOSSEUM_FROZEN_EXECUTABLE"],
            "run",
            str(PROBE_SMOKE),
            "--config",
            str(PROBE_CONFIG),
        ],
        cwd=isolated_cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert '"ep_names": ["contract_probe"]' in proc.stdout
    assert "CONTRACT_PROBE_OK:" in proc.stdout
    assert "CONTRACT_PROBE_REPORT_OK" in proc.stdout
    assert next((isolated_cwd / "outputs").iterdir()).name.endswith("-pass")


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
    proc = run_python_script(BROKEN_LOAD, isolated_cwd, env, python=installed_broken_only)
    combined = (proc.stdout or "") + (proc.stderr or "")
    assert proc.returncode == 2, combined
    assert "PluginRegistrationError" in combined
    assert "contract_broken" in combined

    _pip(installed_broken_only, "uninstall", "-y", BROKEN_DIST)
    clean = subprocess.run(
        [str(installed_broken_only), "-c", "import colosseum as col; print('ok', col.__version__)"],
        cwd=isolated_cwd,
        env=subprocess_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert clean.returncode == 0, clean.stderr
    assert "ok" in clean.stdout
