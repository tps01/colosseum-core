"""Exercise the documented plugin-free procedure and verification-only replay."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_numeric_text_example_and_replay(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    example = repo / "examples" / "evidence_replay.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo)
    env.pop("COLOSSEUM_NO_ARTIFACTS", None)
    cli = [
        sys.executable, "-c", "from colosseum.runner.cli import main; main()", "run", str(example),
    ]

    def run(*args: str) -> None:
        result = subprocess.run(
            cli + list(args), cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    run("--no-artifacts")
    assert not (tmp_path / "outputs").exists()
    run("-o", str(tmp_path / "original"))
    original = next((tmp_path / "original").glob("*-pass"))
    run("-u", str(original), "-o", str(tmp_path / "replay"))
    replay = next((tmp_path / "replay").glob("*-pass"))
    for folder in (original, replay):
        with sqlite3.connect(folder / "execution.sqlite") as db:
            expected = [("rail", "PASS"), ("version", "PASS")]
            measurements = db.execute(
                "SELECT key, status FROM measurements ORDER BY key",
            ).fetchall()
            verifications = db.execute(
                "SELECT key, status FROM verifications ORDER BY key",
            ).fetchall()
            assert measurements == expected
            assert verifications == expected
