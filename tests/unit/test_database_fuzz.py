"""Replay database fuzz seeds through the real manager and writer thread."""

from pathlib import Path

import pytest

from tests.fuzz.database import check_input


@pytest.mark.parametrize(
    "seed", sorted((Path(__file__).parents[1] / "fuzz/database_corpus").iterdir()),
    ids=lambda path: path.name,
)
def test_database_fuzz_seed(seed, tmp_path, monkeypatch):
    # Keep every generated SQLite file under this test's temporary directory.
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))
    check_input(seed.read_bytes())
