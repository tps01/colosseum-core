import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest
from colosseum.runner.cli import run_cli


@pytest.mark.parametrize("no_artifacts", [False, True])
def test_single_interrupt(
    isolated_cwd: Path, capsys: pytest.CaptureFixture[str], *, no_artifacts: bool,
) -> None:
    script = isolated_cwd / "interrupt.py"
    script.write_text(
        "from colosseum.decorators import verification\n"
        "@verification()\ndef check(*, key, result):\n    return result\n"
        "def main():\n    check(key='good', result=True)\n"
        "    check(key='bad', result=False)\n    raise KeyboardInterrupt\n",
        encoding="utf-8",
    )
    args = ["run", str(script), "--no-artifacts"] if no_artifacts else [
        "run", str(script), "--report", "junit", "--report", "wats",
    ]
    with pytest.raises(SystemExit) as exc:
        run_cli(args)
    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert "Overall result: INCOMPLETE (exit 1)" in output
    assert "Overall result: PASS" not in output
    if no_artifacts:
        assert not (isolated_cwd / "outputs").exists()
        return
    run, = (isolated_cwd / "outputs").glob("*-incomplete")
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    assert summary["overall_result"] == "INCOMPLETE"
    assert summary["interruption_reason"] == "Interrupted by user"
    assert summary["verification_counts"]["required"] == {"PASS": 1, "FAIL": 1}
    with sqlite3.connect(run / "execution.sqlite") as db:
        assert db.execute("SELECT overall_result, exit_code FROM run_result").fetchone() == ("INCOMPLETE", 1)
    assert 'type="Interrupted"' in (run / "junit.xml").read_text(encoding="utf-8")
    assert list(run.glob("wats_*.json")) == []


@pytest.mark.parametrize("phase", ["setup", "test", "teardown"])
def test_suite_interrupt_skips_remaining_slots(isolated_cwd: Path, phase: str) -> None:
    (isolated_cwd / "ok.py").write_text("def main():\n    pass\n", encoding="utf-8")
    (isolated_cwd / "stop.py").write_text("def main():\n    raise KeyboardInterrupt\n", encoding="utf-8")
    (isolated_cwd / "extra.py").write_text("def main():\n    raise AssertionError\n", encoding="utf-8")
    scripts = {
        "setup": 'setup = ["stop.py"]\ntests = ["extra.py"]\nteardown = ["extra.py"]',
        "test": 'tests = ["ok.py", "stop.py", "extra.py"]\nteardown = ["extra.py"]',
        "teardown": 'tests = ["ok.py"]\nteardown = ["stop.py", "extra.py"]',
    }
    suite = isolated_cwd / "suite.toml"
    suite.write_text(f'name = "cancel"\n{scripts[phase]}\n', encoding="utf-8")

    assert run_cli(["run-suite", str(suite), "--report", "junit"]) == 1
    run, = (isolated_cwd / "outputs").glob("*-incomplete")
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    assert summary["overall_result"] == "INCOMPLETE"
    assert summary["interruption_reason"] == "Interrupted by user"
    expected = ["INCOMPLETE"] if phase == "setup" else ["PASS", "INCOMPLETE"]
    assert [slot["overall_result"] for slot in summary["all_slots"]] == expected
    assert summary["all_slots"][-1]["phase"] == phase
    assert summary["test_slot_counts"].get("incomplete", 0) == (phase == "test")
    reports = [p for p in run.rglob("junit.xml") if 'type="Interrupted"' in p.read_text(encoding="utf-8")]
    assert len(reports) == 1
    assert (reports[0].parent == run) == (phase != "test")


def test_swallowed_signal_still_cancels_suite(isolated_cwd: Path) -> None:
    (isolated_cwd / "stop.py").write_text(
        "import signal\ndef main():\n    try:\n"
        "        signal.raise_signal(signal.SIGINT)\n    except KeyboardInterrupt:\n        pass\n",
        encoding="utf-8",
    )
    (isolated_cwd / "extra.py").write_text("def main(): raise AssertionError\n", encoding="utf-8")
    suite = isolated_cwd / "suite.toml"
    suite.write_text(
        'name = "caught"\ntests = ["stop.py", "extra.py"]\nteardown = ["extra.py"]\n',
        encoding="utf-8",
    )
    assert run_cli(["run-suite", str(suite)]) == 1
    run, = (isolated_cwd / "outputs").glob("*-incomplete")
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    assert [slot["overall_result"] for slot in summary["all_slots"]] == ["INCOMPLETE"]


def test_first_resource_close_interrupt_preserves_summary(isolated_cwd: Path) -> None:
    script = isolated_cwd / "close.py"
    script.write_text(
        "from pathlib import Path\nfrom colosseum.context import get_context\n"
        "class Interrupting:\n    def close(self): raise KeyboardInterrupt\n"
        "class Other:\n    def close(self): Path('other-closed').touch()\n"
        "def main():\n    get_context().resource_cache.update(first=Interrupting(), second=Other())\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exc:
        run_cli(["run", str(script)])
    assert exc.value.code == 1
    assert (isolated_cwd / "other-closed").exists()
    run, = (isolated_cwd / "outputs").glob("*-incomplete")
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    assert summary["interruption_reason"] == "Interrupted by user"


def test_early_stop_ignores_previous_run(isolated_cwd: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = isolated_cwd / "pass.py"
    script.write_text("def main(): pass\n", encoding="utf-8")
    args = ["run", str(script), "--no-artifacts"]
    with pytest.raises(SystemExit) as exc:
        run_cli(args)
    assert exc.value.code == 0
    marker = isolated_cwd / "stop"
    marker.touch()
    monkeypatch.setenv("COLOSSEUM_GUI_STOP_FILE", str(marker))
    assert run_cli(args) == 1


def test_direct_script_interrupt(tmp_path: Path, subprocess_env: dict[str, str]) -> None:
    script = tmp_path / "direct.py"
    (tmp_path / "core.toml").touch()
    script.write_text(
        "import colosseum as col\ncol.config.load_config('core.toml')\nraise KeyboardInterrupt\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(script)], cwd=tmp_path, env=subprocess_env,
        capture_output=True, text=True, timeout=10, check=False,
    )
    assert result.returncode != 0
    run, = (tmp_path / "outputs").glob("*-incomplete")
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    assert summary["overall_result"] == "INCOMPLETE"
    assert summary["interruption_reason"] == "Interrupted by user"


def test_endex_in_finally_during_interrupt(isolated_cwd: Path) -> None:
    script = isolated_cwd / "finalize.py"
    script.write_text(
        "from colosseum import endex\ndef main():\n    try:\n"
        "        raise KeyboardInterrupt\n    finally:\n        endex()\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exc:
        run_cli(["run", str(script)])
    assert exc.value.code == 1
    assert len(list((isolated_cwd / "outputs").glob("*-incomplete"))) == 1


@pytest.mark.skipif(os.name != "posix", reason="POSIX process signals")
@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_cli_process_signal(tmp_path: Path, sig: signal.Signals) -> None:
    script = tmp_path / "wait.py"
    script.write_text(
        "from pathlib import Path\nimport time\n"
        "def main():\n    Path('ready').touch()\n    time.sleep(60)\n",
        encoding="utf-8",
    )
    root = str(Path(__file__).resolve().parents[2])
    env = {**os.environ, "PYTHONPATH": root}
    with subprocess.Popen(
        [sys.executable, "-m", "colosseum.runner.cli", "run", str(script), "--no-artifacts"],
        cwd=tmp_path, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    ) as runner:
        try:
            deadline = time.monotonic() + 10
            while not (tmp_path / "ready").exists() and runner.poll() is None:
                assert time.monotonic() < deadline
                time.sleep(0.05)
            assert runner.poll() is None
            runner.send_signal(sig)
            output, _ = runner.communicate(timeout=5)
        finally:
            if runner.poll() is None:
                runner.kill()
        assert runner.returncode == 1
    assert "Overall result: INCOMPLETE (exit 1)" in output
