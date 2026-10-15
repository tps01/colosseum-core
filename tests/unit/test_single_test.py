"""Runner loads scripts with the script directory on sys.path."""

from __future__ import annotations

from pathlib import Path

from colosseum.runner.single_test import run_script


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
