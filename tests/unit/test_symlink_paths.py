"""Regression coverage for native paths and persisted filesystem references."""

from __future__ import annotations

import logging
import os
import sqlite3
import stat
import subprocess
import sys
import tarfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from colosseum.config.parameters import resolve_parameters_path
from colosseum.config.suite_inputs import SuiteInputs
from colosseum.context import init_context
from colosseum.database.artifact_paths import (
    relativize_imported_artifact,
    resolve_stored_artifact,
    stored_artifact_path,
)
from colosseum.paths import absolute_path, sqlite_readonly_uri
from colosseum.runner.provenance import InputFile, hash_inputs
from colosseum.runner.runtime import allocate_run_directory, rename_run_directory_for_result
from colosseum.runner.single_test import _call_script_main
from colosseum.runner.suite_toml import load_suite_toml
from colosseum.tools.build_executable import _launcher_name, archive_app
from scripts.cleanup import _collect_paths
from tests.support.e2e_specifications import run_suite_cli


def _link(path: Path, target: Path, *, directory: bool = False) -> None:
    try:
        path.symlink_to(target, target_is_directory=directory)
    except OSError as exc:
        if getattr(exc, "winerror", None) != 1314:
            raise
        pytest.skip(f"Symlink creation requires Windows Developer Mode or elevation: {exc}")


@pytest.mark.skipif(os.name == "nt", reason="Win32 normalizes parent components before lookup")
def test_readonly_sqlite_matches_native_parent_traversal(tmp_path: Path) -> None:
    lexical = tmp_path / "lexical"
    native = tmp_path / "native"
    lexical.mkdir()
    (native / "child").mkdir(parents=True)
    _link(lexical / "jump", native / "child", directory=True)
    for folder in (lexical, native):
        connection = sqlite3.connect(folder / "choice.db")
        connection.execute(f"pragma user_version={1 if folder == native else 2}")
        connection.close()
    via = lexical / "jump" / ".." / "choice.db"
    assert via.read_bytes() == absolute_path(via).read_bytes()
    connection = sqlite3.connect(sqlite_readonly_uri(via), uri=True)
    try:
        assert connection.execute("pragma user_version").fetchone() == (1,)
    finally:
        connection.close()


def test_linked_suite_and_script_use_target_siblings(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    script = target / "script.py"
    script.write_text(
        "from symlink_sibling_helper import value\n"
        "def main():\n    assert value == 7\n"
        "if __name__ == '__main__':\n    main()\n",
        encoding="utf-8",
    )
    (target / "symlink_sibling_helper.py").write_text("value = 7", encoding="utf-8")
    for name in ("config.toml", "metadata.yaml", "parameters.toml"):
        (target / name).touch()
    script_alias = tmp_path / "alias.py"
    _link(script_alias, script)
    native = subprocess.run([sys.executable, str(script_alias)], capture_output=True, check=False)
    init_context(test_case_name="linked", no_artifacts=True)
    try:
        if sys.platform == "win32":
            assert native.returncode != 0
            assert b"ModuleNotFoundError" in native.stderr
            with pytest.raises(ModuleNotFoundError, match="symlink_sibling_helper"):
                _call_script_main(script_alias)
        else:
            assert native.returncode == 0, native.stderr
            _call_script_main(script_alias)
    finally:
        sys.modules.pop("symlink_sibling_helper", None)
    assert resolve_parameters_path(script_path=script_alias) == target / "parameters.toml"
    suite = target / "suite.toml"
    suite.write_text('name = "linked"\ntests = ["../alias.py"]\n', encoding="utf-8")
    suite_alias = tmp_path / "suite.toml"
    _link(suite_alias, suite)
    entry = load_suite_toml(suite_alias).tests[0]
    assert entry.path.samefile(script)
    assert SuiteInputs({}).test_path("config", entry) == target / "config.toml"
    assert SuiteInputs({}).test_path("metadata", entry) == target / "metadata.yaml"


def test_provenance_keeps_aliases_and_logs_cycles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    from colosseum.runner import provenance

    reads = []
    target = tmp_path / "file"
    target.write_text("input", encoding="utf-8")
    alias = tmp_path / "alias"
    cycle = tmp_path / "cycle"
    _link(alias, target)
    _link(cycle, cycle)
    original = provenance._md5_file

    def count(path: Path) -> str:
        reads.append(path)
        return original(path)

    monkeypatch.setattr(provenance, "_md5_file", count)
    logger = logging.Logger("input-test")
    logger.addHandler(caplog.handler)
    rows = hash_inputs([InputFile("config", path) for path in (target, cycle, alias)], logger=logger)
    assert [row["path"] for row in rows] == [str(target), str(alias)]
    assert len(reads) == 1
    assert f"Could not hash config {cycle}" in caplog.text


@pytest.mark.parametrize("fail_fast", [False, True])
def test_suite_defers_a_cyclic_config_to_its_slot(
    core_config: Path, isolated_cwd: Path, subprocess_env: dict[str, str], *, fail_fast: bool,
) -> None:
    for name in ("before", "bad", "after"):
        source = (
            "from pathlib import Path\n"
            "import colosseum as col\n"
            "def main():\n"
            f"    Path({name!r}).touch()\n"
            "    col.endex()\n"
        )
        (isolated_cwd / f"{name}.py").write_text(source, encoding="utf-8")
    cycle = isolated_cwd / "cycle.toml"
    _link(cycle, cycle)
    suite = isolated_cwd / "suite.toml"
    suite.write_text(
        f'name = "linked"\nfail_fast = {str(fail_fast).lower()}\n'
        'tests = ["before.py", {path = "bad.py", config = "cycle.toml"}, "after.py"]\n',
        encoding="utf-8",
    )
    result = run_suite_cli(suite, core_config, isolated_cwd, subprocess_env)
    assert result.returncode == 1
    assert (isolated_cwd / "before").is_file()
    assert not (isolated_cwd / "bad").exists()
    assert (isolated_cwd / "after").is_file() is (not fail_fast)


@pytest.mark.skipif(os.name != "nt", reason="Windows drive spelling")
def test_absolute_path_keeps_a_windows_drive_letter() -> None:
    path = Path("Z:/mapped drive/capture/../execution.sqlite")
    assert absolute_path(path) == Path("Z:/mapped drive/execution.sqlite")
    assert sqlite_readonly_uri(path) == "file:///Z:/mapped%20drive/execution.sqlite?mode=ro"


def test_artifact_links_pin_targets(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    internal = run / "inside"
    external = tmp_path / "outside"
    internal.touch()
    external.touch()
    local_alias = run / "local"
    remote_alias = run / "remote"
    _link(local_alias, Path(internal.name))
    _link(remote_alias, external)
    assert stored_artifact_path(local_alias, run) == "inside"
    saved = stored_artifact_path(Path("remote"), run)
    imported = relativize_imported_artifact("local", run)
    assert imported is not None and Path(imported).samefile(internal)
    remote_alias.unlink()
    _link(remote_alias, internal)
    assert Path(saved).samefile(external)
    external.unlink()
    final = rename_run_directory_for_result(run, "pass")
    (final / "outside").touch()
    assert resolve_stored_artifact(saved, run_dir=final) == external
    assert resolve_stored_artifact("inside", run_dir=final).is_file()


def test_cleanup_prunes_links_including_fixed_ancestors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts import cleanup

    root = tmp_path / "checkout"
    root.mkdir()
    external = tmp_path / "external"
    wheels = external / "python-wheels"
    wheels.mkdir(parents=True)
    sentinel = wheels / "sentinel.pyc"
    sentinel.touch()
    for name in ("share", ".venv", "junction"):
        alias = root / name
        if sys.platform == "win32":
            subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(alias), str(external)],
                capture_output=True,
                check=True,
            )
            assert alias.lstat().st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT
        else:
            _link(alias, external, directory=True)
    garbage = root / "ordinary.pyc"
    garbage.touch()
    assert _collect_paths(root, keep_venvs=True) == [garbage]
    monkeypatch.setattr(cleanup, "_repo_root", lambda: root)
    assert cleanup.main(["--keep-venvs"]) == 0
    assert sentinel.is_file()
    assert all((root / name).is_dir() for name in ("share", ".venv", "junction"))


def test_run_directory_allocation_is_exclusive(tmp_path: Path) -> None:
    with ThreadPoolExecutor(8) as pool:
        paths = set(pool.map(lambda _: allocate_run_directory(tmp_path, "same"), range(24)))
    assert len(paths) == 24
    assert all(path.is_dir() for path in paths)


def test_rename_skips_dangling_destination(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    occupied = tmp_path / "run-pass"
    _link(occupied, tmp_path / "missing", directory=True)
    assert rename_run_directory_for_result(run, "pass").name == "run-pass_1"
    assert occupied.is_symlink()


def test_archive_link_policy_preserves_existing_output(tmp_path: Path) -> None:
    app = tmp_path / "colosseum"
    (app / "_internal").mkdir(parents=True)
    (app / _launcher_name()).touch()
    target = app / "_internal" / "target"
    target.touch()
    alias = target.with_name("alias")
    _link(alias, Path(target.name))
    previous = tmp_path / "colosseum.zip"
    previous.write_bytes(b"existing")
    with pytest.raises(SystemExit, match="cannot archive link"):
        archive_app(app, kind="zip")
    assert previous.read_bytes() == b"existing"
    tar = archive_app(app, kind="gztar")
    with tarfile.open(tar) as archive:
        assert archive.getmember("colosseum/_internal/alias").linkname == "target"
    alias.unlink()
    _link(alias, Path("missing"))
    with pytest.raises(SystemExit, match="Invalid archive link"):
        archive_app(app, kind="gztar")
    alias.unlink()
    outside = tmp_path / "outside"
    outside.touch()
    _link(alias, Path("../../outside"))
    with pytest.raises(SystemExit, match="Invalid archive link"):
        archive_app(app, kind="gztar")
