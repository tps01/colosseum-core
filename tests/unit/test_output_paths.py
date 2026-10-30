"""U-OUT-01: output directory naming."""

from __future__ import annotations

import re

from colosseum.runner.runtime import (
    allocate_run_directory,
    rename_run_directory_for_result,
    sanitize_logical_name,
)


def test_sanitize_strips_unsafe_characters() -> None:
    assert sanitize_logical_name("my test!") == "my_test"
    assert sanitize_logical_name("") == "run"


def test_allocate_run_directory_format_and_collision(isolated_cwd) -> None:
    outputs_root = isolated_cwd / "outputs"
    first = allocate_run_directory(outputs_root, "smoke test")
    first.mkdir()
    second = allocate_run_directory(outputs_root, "smoke test")
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{6}_smoke_test(_\d+)?$")
    assert pattern.match(first.name)
    assert second != first
    assert second.name.endswith("_1") or first.name != second.name


def test_allocate_run_directory_under_parent(isolated_cwd) -> None:
    outputs_root = isolated_cwd / "outputs"
    parent = outputs_root / "suite_container"
    parent.mkdir(parents=True)
    child = allocate_run_directory(outputs_root, "probe", parent=parent)
    assert child.parent == parent
    assert child.name.startswith("20")
    assert child.name.endswith("_probe")


def test_rename_run_directory_for_result_appends_status(isolated_cwd) -> None:
    run_dir = isolated_cwd / "outputs" / "2026-01-01_120000_smoke"
    run_dir.mkdir(parents=True)
    final_dir = rename_run_directory_for_result(run_dir, "FAIL")
    assert final_dir.name == "2026-01-01_120000_smoke-fail"
    assert final_dir.is_dir()
    assert not run_dir.exists()


def test_rename_run_directory_for_result_avoids_collision(isolated_cwd) -> None:
    run_dir = isolated_cwd / "outputs" / "2026-01-01_120000_smoke"
    existing = isolated_cwd / "outputs" / "2026-01-01_120000_smoke-pass"
    run_dir.mkdir(parents=True)
    existing.mkdir()
    final_dir = rename_run_directory_for_result(run_dir, "PASS")
    assert final_dir.name == "2026-01-01_120000_smoke-pass_1"
    assert final_dir.is_dir()


def test_rename_run_directory_for_result_keeps_dir_after_oserror(
    isolated_cwd, monkeypatch, capsys,
) -> None:
    from pathlib import Path

    run_dir = isolated_cwd / "outputs" / "2026-01-01_120000_smoke"
    run_dir.mkdir(parents=True)
    (run_dir / "summary.txt").write_text("ok\n", encoding="utf-8")

    def boom(self: Path, target: Path) -> Path:  # noqa: ARG001
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(Path, "rename", boom)
    final_dir = rename_run_directory_for_result(
        run_dir, "FAIL", retries=2, initial_delay_s=0.0,
    )
    assert final_dir == run_dir
    assert run_dir.is_dir()
    assert (run_dir / "summary.txt").is_file()
    err = capsys.readouterr().err
    assert "failed to rename" in err
    assert "leaving directory unrenamed" in err
