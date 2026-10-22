"""Runner loads scripts with the script directory on sys.path."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from colosseum.runner.single_test import ScriptRunError, run_script


def test_run_script_imports_sibling_module(unit_runtime_context, tmp_path: Path, monkeypatch) -> None:
    _ = unit_runtime_context
    (tmp_path / "helper_mod.py").write_text("VALUE = 7\n", encoding="utf-8")
    script = tmp_path / "case.py"
    script.write_text(
        "from helper_mod import VALUE\n\n"
        "def main() -> None:\n"
        "    assert VALUE == 7\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path.parent)
    run_script(script)


def test_run_script_restores_sys_path_and_keeps_sibling(
    unit_runtime_context, tmp_path: Path, monkeypatch,
) -> None:
    _ = unit_runtime_context
    (tmp_path / "shared_helper.py").write_text("VALUE = 1\n", encoding="utf-8")
    first = tmp_path / "first.py"
    first.write_text(
        "import shared_helper\n"
        "shared_helper.VALUE = 42\n\n"
        "def main() -> None:\n"
        "    assert shared_helper.VALUE == 42\n",
        encoding="utf-8",
    )
    second = tmp_path / "second.py"
    second.write_text(
        "import shared_helper\n\n"
        "def main() -> None:\n"
        "    assert shared_helper.VALUE == 42\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path.parent)
    before = list(sys.path)
    run_script(first)
    assert list(sys.path) == before
    assert unit_runtime_context.active_script_path is None
    assert "shared_helper" in sys.modules
    first_mod = sys.modules["shared_helper"]
    run_script(second)
    assert list(sys.path) == before
    assert unit_runtime_context.active_script_path is None
    assert sys.modules["shared_helper"] is first_mod


def test_run_script_does_not_replace_cached_module(
    unit_runtime_context, tmp_path: Path, monkeypatch,
) -> None:
    _ = unit_runtime_context
    cached = types.ModuleType("cached_sibling")
    cached.VALUE = 99  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "cached_sibling", cached)
    (tmp_path / "cached_sibling.py").write_text("VALUE = 1\n", encoding="utf-8")
    script = tmp_path / "case.py"
    script.write_text(
        "import cached_sibling\n\n"
        "def main() -> None:\n"
        "    assert cached_sibling.VALUE == 99\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path.parent)
    run_script(script)
    assert sys.modules["cached_sibling"] is cached


def test_run_script_restores_sys_path_on_main_raise(
    unit_runtime_context, tmp_path: Path, monkeypatch,
) -> None:
    _ = unit_runtime_context
    script = tmp_path / "boom.py"
    script.write_text(
        "def main() -> None:\n"
        "    raise RuntimeError('boom')\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path.parent)
    before = list(sys.path)
    with pytest.raises(ScriptRunError):
        run_script(script)
    assert list(sys.path) == before
    assert unit_runtime_context.active_script_path is None


def test_run_script_restores_sys_path_on_sys_exit(
    unit_runtime_context, tmp_path: Path, monkeypatch,
) -> None:
    _ = unit_runtime_context
    script = tmp_path / "exit_case.py"
    script.write_text(
        "import sys\n\n"
        "def main() -> None:\n"
        "    sys.exit(2)\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path.parent)
    before = list(sys.path)
    with pytest.raises(ScriptRunError):
        run_script(script)
    assert list(sys.path) == before
    assert unit_runtime_context.active_script_path is None


def test_run_script_prefers_script_dir_when_already_later_on_path(
    unit_runtime_context, tmp_path: Path, monkeypatch,
) -> None:
    _ = unit_runtime_context
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    (decoy / "path_probe.py").write_text("SOURCE = 'decoy'\n", encoding="utf-8")
    (tmp_path / "path_probe.py").write_text("SOURCE = 'script'\n", encoding="utf-8")
    script = tmp_path / "case.py"
    script.write_text(
        "from path_probe import SOURCE\n\n"
        "def main() -> None:\n"
        "    assert SOURCE == 'script'\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path.parent)
    script_dir = str(tmp_path.resolve())
    decoy_dir = str(decoy.resolve())
    # Script directory later on the path; decoy earlier must not win.
    monkeypatch.setattr(sys, "path", [decoy_dir, script_dir, *sys.path])
    before = list(sys.path)
    run_script(script)
    assert list(sys.path) == before
    assert unit_runtime_context.active_script_path is None
