"""Teardown slot records a verification. Procedure mode must not skip this phase."""

from __future__ import annotations

from pathlib import Path

import colosseum as col

from tests.support.core_api import measure_value, verify_value

_CONFIG = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "core.toml"


def main() -> None:
    col.config.load_config(str(_CONFIG))
    measure_value(key="teardown", value=1.0)
    verify_value(key="teardown", expected_val=1.0, tolerance=0.1)
