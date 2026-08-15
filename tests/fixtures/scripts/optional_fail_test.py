"""Required checks pass; optional verification fails — run must still exit 0."""

from __future__ import annotations

from pathlib import Path

import colosseum as col

from tests.support.core_api import measure_value, verify_value

_REPO = Path(__file__).resolve().parents[3]
_CONFIG = _REPO / "tests" / "fixtures" / "core.toml"


def main() -> None:
    col.config.load_config(str(_CONFIG))
    measure_value(key="required", value=3.3)
    verify_value(key="required", expected_val=3.3, tolerance=0.1)
    measure_value(key="optional", value=2.2)
    verify_value(key="optional", expected_val=1.8, tolerance=0.1, optional=True)


if __name__ == "__main__":
    main()
    col.endex()
