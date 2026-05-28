"""U-OUT-01: output directory naming."""

from __future__ import annotations

import re

from colosseum.output.paths import _sanitize, allocate_run_directory


def test_sanitize_strips_unsafe_characters() -> None:
    assert _sanitize("my test!") == "my_test"
    assert _sanitize("") == "run"


def test_allocate_run_directory_format_and_collision(isolated_cwd) -> None:
    first = allocate_run_directory(isolated_cwd, "smoke test")
    first.mkdir()
    second = allocate_run_directory(isolated_cwd, "smoke test")
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{6}_smoke_test(_\d+)?$")
    assert pattern.match(first.name)
    assert second != first
    assert second.name.endswith("_1") or first.name != second.name
