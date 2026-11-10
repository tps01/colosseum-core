"""Test-slot verification body fails the suite if procedure mode does not skip it."""

from __future__ import annotations

from pathlib import Path

import colosseum as col
from colosseum.decorators import verification

from tests.support.core_api import measure_value

_CONFIG = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "core.toml"


@verification
def must_not_run(*, key: str, expected_val: float, tolerance: float) -> float:
    raise RuntimeError("verification body ran during procedure mode")


def main() -> None:
    col.config.load_config(str(_CONFIG))
    measure_value(key="during", value=1.0)
    must_not_run(key="during", expected_val=1.0, tolerance=0.1)
