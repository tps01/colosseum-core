"""Required verification of a real measurement outside its limit (FAIL, exit 1)."""

from __future__ import annotations

from pathlib import Path

import colosseum as col

from tests.support.core_api import measure_value, verify_value

_CONFIG = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "core.toml"


def main() -> None:
    col.config.load_config(str(_CONFIG))
    measure_value(key="rail", value=3.3)
    verify_value(key="rail", expected_val=5.0, tolerance=0.1)
