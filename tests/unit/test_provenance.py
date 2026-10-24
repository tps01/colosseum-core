"""Output-directory preflight and once-per-run provenance."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from types import SimpleNamespace

import colosseum.context as context_module
import colosseum.runner.provenance as provenance_module
import pytest
from colosseum.context import init_context
from colosseum.database.manager import DatabaseManager
from colosseum.logging.setup import close_logger_handlers
from colosseum.runner.cli import run_cli
from colosseum.runner.provenance import (
    InputFile,
    hash_inputs,
    record_single_provenance,
    record_suite_provenance,
    suite_input_files,
    write_provenance_database,
)
from colosseum.runner.run_options import RunOptions
from colosseum.runner.runtime import (
    OutputNotWritableError,
    ensure_outputs_writable,
    ensure_runtime_ready,
    ensure_suite_runtime_ready,
)
from colosseum.summary.writer import SuiteSummaryWriter, SummaryWriter


class _Dist:
    def __init__(
        self,
        name: str,
        version: str,
        *,
        plugin: bool = False,
        path: str = "",
        direct_url: str | None = None,
    ) -> None:
        self.metadata = {"Name": name}
        self.version = version
        self.entry_points = [SimpleNamespace(group="colosseum.plugins")] if plugin else []
        self._path = path
        self._direct_url = direct_url

    def read_text(self, name: str) -> str | None:
        if name == "direct_url.json":
            return self._direct_url
        return None


def _close_runtime(ctx: context_module.RuntimeContext) -> None:
    if ctx.logger is not None:
        close_logger_handlers(ctx.logger)
    if ctx.db.is_initialized():
        ctx.db.close()
    context_module._ACTIVE_CONTEXT = None


def test_outputs_root_probe_accepts_temp_directory(tmp_path: Path) -> None:
    ensure_outputs_writable(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_probe_wraps_write_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _deny(_self: Path, _data: bytes) -> int:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "write_bytes", _deny)
    with pytest.raises(OutputNotWritableError, match="Permission denied"):
        ensure_outputs_writable(tmp_path)


def test_unwritable_outputs_raise_before_run_directory(tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    blocked.write_text("x", encoding="utf-8")
    ctx = init_context(
        test_case_name="blocked",
        run_options=RunOptions(outputs_root=blocked),
    )
    try:
        with pytest.raises(OutputNotWritableError, match="not writable"):
            ensure_runtime_ready(ctx)
        assert ctx.output_dir is None
        assert set(tmp_path.iterdir()) == {blocked}
    finally:
        _close_runtime(ctx)


def test_suite_runtime_refuses_unwritable_root(tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    blocked.write_text("x", encoding="utf-8")
    ctx = init_context(
        test_case_name="suite",
        suite_name="suite",
        run_options=RunOptions(outputs_root=blocked),
    )
    try:
        with pytest.raises(OutputNotWritableError, match="not writable"):
            ensure_suite_runtime_ready(ctx, "suite")
        assert ctx.suite_output_dir is None
        assert set(tmp_path.iterdir()) == {blocked}
    finally:
        _close_runtime(ctx)


def test_no_artifacts_skips_writable_probe(tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    blocked.write_text("x", encoding="utf-8")
    script = tmp_path / "script.py"
    script.write_text("def main():\n    pass\n", encoding="utf-8")
    ctx = init_context(
        test_case_name="memory",
        no_artifacts=True,
        run_options=RunOptions(outputs_root=blocked),
    )
    try:
        ensure_runtime_ready(ctx)
        record_single_provenance(ctx, script, None)
        assert ctx.output_dir is None
        sections = {row["section"] for row in ctx.db.fetch_table_rows("provenance")}
        assert sections == {"platform", "packages", "inputs", "repositories"}
        assert set(tmp_path.iterdir()) == {blocked, script}
    finally:
        _close_runtime(ctx)


def test_cli_cancels_when_output_root_is_not_a_directory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    blocked = tmp_path / "blocked"
    blocked.write_text("nope", encoding="utf-8")
    marker = tmp_path / "ran.txt"
    script = tmp_path / "should_not_run.py"
    script.write_text(
        "from pathlib import Path\n"
        "def main():\n"
        f"    Path({str(marker)!r}).write_text('ran', encoding='utf-8')\n",
        encoding="utf-8",
    )
    try:
        with pytest.raises(SystemExit) as exc:
            run_cli(["run", str(script), "-o", str(blocked)])
        assert exc.value.code == 1
        assert "not writable" in capsys.readouterr().err
        assert not marker.exists()
        assert set(tmp_path.iterdir()) == {blocked, script}
    finally:
        ctx = context_module._ACTIVE_CONTEXT
        if ctx is not None:
            _close_runtime(ctx)


def test_snapshot_hashes_each_path_once_and_sorts_packages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = tmp_path / "check.py"
    payload = b"print(1)\n"
    script.write_bytes(payload)
    monkeypatch.setattr(
        provenance_module,
        "distributions",
        lambda: [
            _Dist("zzz", "1"),
            _Dist("colosseum-equipment", "0.7.0", plugin=True),
            _Dist("Aaa", "2"),
        ],
    )

    def _missing(name: str) -> _Dist:
        raise PackageNotFoundError(name)

    monkeypatch.setattr(provenance_module, "distribution", _missing)
    calls = {"n": 0}
    real_md5 = provenance_module._md5_file

    def _counting(path: Path) -> str:
        calls["n"] += 1
        return real_md5(path)

    monkeypatch.setattr(provenance_module, "_md5_file", _counting)
    snapshot = provenance_module.collect_provenance(
        [InputFile("script", script), InputFile("test", script)],
    )
    assert calls["n"] == 1
    assert set(snapshot["platform"]) == {  # type: ignore[arg-type]
        "system",
        "release",
        "version",
        "machine",
        "python_version",
        "python_implementation",
        "executable",
    }
    assert snapshot["platform"]["executable"] == sys.executable  # type: ignore[index]
    packages = snapshot["packages"]
    assert packages["versions"] == {  # type: ignore[index]
        "Aaa": "2",
        "colosseum-equipment": "0.7.0",
        "zzz": "1",
    }
    assert packages["plugins"] == ["colosseum-equipment"]  # type: ignore[index]
    digest = hashlib.md5(payload, usedforsecurity=False).hexdigest()
    inputs = snapshot["inputs"]
    assert inputs[0]["md5"] == digest  # type: ignore[index]
    assert inputs[1]["md5"] == digest  # type: ignore[index]
    assert hash_inputs([InputFile("script", tmp_path / "missing.py")]) == []


def test_selected_install_wins_and_editable_repo_is_recorded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "checkout"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=provenance@example.com",
            "-c",
            "user.name=provenance",
            "commit",
            "--allow-empty",
            "-m",
            "init",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    direct_url = json.dumps(
        {"url": repo.as_uri(), "dir_info": {"editable": True}},
    )
    leftover = _Dist("colosseum-core", "0.16.0", path=str(tmp_path / "old.dist-info"))
    selected = _Dist(
        "colosseum-core",
        "0.17.6",
        path=str(tmp_path / "new.dist-info"),
        direct_url=direct_url,
    )
    monkeypatch.setattr(provenance_module, "distributions", lambda: [leftover, selected])
    monkeypatch.setattr(provenance_module, "distribution", lambda _name: selected)

    snapshot = provenance_module.collect_provenance([])
    packages = snapshot["packages"]
    assert packages["versions"]["colosseum-core"] == "0.17.6"  # type: ignore[index]
    installs = packages["installs"]  # type: ignore[index]
    by_version = {row["version"]: row for row in installs}
    assert by_version["0.16.0"]["selected"] is False
    assert by_version["0.17.6"]["selected"] is True
    assert by_version["0.17.6"]["editable"]["commit"]
    assert by_version["0.17.6"]["editable"]["dirty"] is False
    repositories = snapshot["repositories"]
    assert Path(str(repositories[0]["path"])).resolve() == repo.resolve()  # type: ignore[index]
    assert repositories[0]["dirty"] is False  # type: ignore[index]


def test_suite_inputs_prefer_cli_parameters_over_sibling(tmp_path: Path) -> None:
    script = tmp_path / "t.py"
    script.write_text("def main():\n    pass\n", encoding="utf-8")
    sibling = tmp_path / "parameters.toml"
    sibling.write_text("[rail]\nexpected = 1\n", encoding="utf-8")
    cli_parameters = tmp_path / "cli.toml"
    cli_parameters.write_text("[rail]\nexpected = 2\n", encoding="utf-8")
    suite_path = tmp_path / "suite.toml"
    suite_path.write_text('name = "demo"\n', encoding="utf-8")
    ctx = init_context(
        test_case_name="demo",
        suite_name="demo",
        run_options=RunOptions(parameters_path=cli_parameters),
    )
    try:
        rows = hash_inputs(
            suite_input_files(
                ctx,
                suite_path=suite_path,
                setup=[],
                tests=[(script, None), (script, None)],
                between_tests=[],
                teardown=[],
            ),
        )
    finally:
        _close_runtime(ctx)
    parameter_rows = [row for row in rows if row["role"] == "parameters"]
    assert len(parameter_rows) == 1
    assert parameter_rows[0]["path"] == str(cli_parameters.resolve())
    assert parameter_rows[0]["md5"] == hashlib.md5(
        cli_parameters.read_bytes(),
        usedforsecurity=False,
    ).hexdigest()


def test_suite_inputs_include_sibling_parameters_once(tmp_path: Path) -> None:
    script = tmp_path / "t.py"
    script.write_text("def main():\n    pass\n", encoding="utf-8")
    sibling = tmp_path / "parameters.toml"
    sibling.write_text("[rail]\nexpected = 1\n", encoding="utf-8")
    suite_path = tmp_path / "suite.toml"
    suite_path.write_text('name = "demo"\n', encoding="utf-8")
    ctx = init_context(test_case_name="demo", suite_name="demo")
    try:
        rows = hash_inputs(
            suite_input_files(
                ctx,
                suite_path=suite_path,
                setup=[],
                tests=[(script, None)],
                between_tests=[],
                teardown=[],
            ),
        )
    finally:
        _close_runtime(ctx)
    parameter_rows = [row for row in rows if row["role"] == "parameters"]
    assert len(parameter_rows) == 1
    assert parameter_rows[0]["md5"] == hashlib.md5(
        sibling.read_bytes(),
        usedforsecurity=False,
    ).hexdigest()


def test_provenance_database_round_trip(tmp_path: Path) -> None:
    database = DatabaseManager()
    database.initialize(tmp_path / "execution.sqlite")
    try:
        snapshot = {
            "platform": {"system": "TestOS"},
            "packages": {"versions": {"colosseum-equipment": "0.7.0"}, "plugins": []},
            "inputs": [{"role": "script", "path": "t.py", "md5": "abc"}],
        }
        write_provenance_database(database, snapshot)
        rows = {
            str(row["section"]): json.loads(str(row["payload_json"]))
            for row in database.fetch_table_rows("provenance")
        }
    finally:
        database.close()
    assert rows["platform"] == {"system": "TestOS"}
    assert rows["packages"]["versions"]["colosseum-equipment"] == "0.7.0"
    assert rows["inputs"][0]["role"] == "script"


def test_summary_json_includes_provenance_for_single_run(
    unit_runtime_context: context_module.RuntimeContext,
) -> None:
    ctx = unit_runtime_context
    out = ctx.output_dir
    assert out is not None
    ctx.provenance = {
        "platform": {"system": "TestOS"},
        "packages": {"versions": {}, "plugins": []},
        "inputs": [],
    }
    SummaryWriter().write(out, ctx.result_aggregator, ctx)
    text = (out / "summary.txt").read_text(encoding="utf-8")
    payload = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert "Provenance" not in text
    assert payload["provenance"]["platform"]["system"] == "TestOS"


def test_slot_summary_omits_suite_provenance(
    unit_runtime_context: context_module.RuntimeContext,
) -> None:
    ctx = unit_runtime_context
    out = ctx.output_dir
    assert out is not None
    ctx.session.kind = "suite"
    ctx.provenance = {"platform": {"system": "TestOS"}}
    SummaryWriter().write(out, ctx.result_aggregator, ctx)
    text = (out / "summary.txt").read_text(encoding="utf-8")
    payload = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert "Provenance" not in text
    assert "provenance" not in payload


def test_suite_summary_includes_container_provenance(
    unit_runtime_context: context_module.RuntimeContext,
) -> None:
    ctx = unit_runtime_context
    root = ctx.output_dir
    assert root is not None
    container = root / "container"
    container.mkdir()
    ctx.provenance = {
        "platform": {"system": "TestOS"},
        "packages": {"versions": {}, "plugins": []},
        "inputs": [],
    }
    SuiteSummaryWriter().write(container, ctx, exit_code=0, overall="PASS")
    text = (container / "summary.txt").read_text(encoding="utf-8")
    payload = json.loads((container / "summary.json").read_text(encoding="utf-8"))
    assert "Provenance" not in text
    assert payload["provenance"]["platform"]["system"] == "TestOS"


def test_single_run_provenance_skips_console(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    script = tmp_path / "check.py"
    script.write_text("def main():\n    pass\n", encoding="utf-8")
    ctx = init_context(
        test_case_name="check",
        run_options=RunOptions(outputs_root=tmp_path / "outputs"),
    )
    try:
        ensure_runtime_ready(ctx)
        record_single_provenance(ctx, script, None)
        record_single_provenance(ctx, script, None)
        captured = capsys.readouterr()
        assert "Provenance:" not in captured.out
        assert ctx.output_dir is not None
        log_text = (ctx.output_dir / "debug.log").read_text(encoding="utf-8")
        assert log_text.count("Provenance: platform=") == 1
        sections = {row["section"] for row in ctx.db.fetch_table_rows("provenance")}
        assert sections == {"platform", "packages", "inputs", "repositories"}
    finally:
        _close_runtime(ctx)


def test_suite_provenance_is_container_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from colosseum.runner.runtime import begin_script_slot

    script = tmp_path / "pass_test.py"
    script.write_text("def main():\n    pass\n", encoding="utf-8")
    suite_path = tmp_path / "suite.toml"
    suite_path.write_text('name = "demo"\n', encoding="utf-8")
    ctx = init_context(
        test_case_name="demo",
        suite_name="demo",
        run_options=RunOptions(outputs_root=tmp_path / "outputs"),
    )
    try:
        ensure_suite_runtime_ready(ctx, "demo")
        record_suite_provenance(
            ctx,
            suite_path=suite_path,
            setup=[],
            tests=[(script, None)],
            between_tests=[],
            teardown=[],
        )
        assert "Provenance:" not in capsys.readouterr().out
        container = ctx.suite_output_dir
        assert container is not None
        assert "Provenance: packages=" in (container / "debug.log").read_text(encoding="utf-8")
        container_db = DatabaseManager()
        container_db.open_readonly(container / "execution.sqlite")
        try:
            stored = {row["section"] for row in container_db.fetch_table_rows("provenance")}
        finally:
            container_db.close()
        assert stored == {"platform", "packages", "inputs", "repositories"}

        begin_script_slot(ctx, script.stem, phase="test", affects_suite_result=True)
        slot_dir = ctx.output_dir
        assert slot_dir is not None
        assert "Provenance:" not in (slot_dir / "debug.log").read_text(encoding="utf-8")
        assert ctx.db.fetch_table_rows("provenance") == []
        SummaryWriter().write(slot_dir, ctx.result_aggregator, ctx)
        slot_summary = json.loads((slot_dir / "summary.json").read_text(encoding="utf-8"))
        assert "provenance" not in slot_summary
    finally:
        _close_runtime(ctx)
