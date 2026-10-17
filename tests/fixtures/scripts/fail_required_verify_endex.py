"""Required verification FAIL then explicit col.endex() (suite fail_fast metadata)."""

from __future__ import annotations

from pathlib import Path

import colosseum as col

from tests.support.core_api import verify_value

_CONFIG = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "core.toml"


def main() -> None:
    col.config.load_config(str(_CONFIG))
    verify_value(key="missing", expected_val=3.3, tolerance=0.1)
    col.endex()
