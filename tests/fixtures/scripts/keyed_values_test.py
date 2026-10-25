"""Keyed measurement and verification for dry-run and parameter export."""

from __future__ import annotations

from pathlib import Path

import colosseum as col

from tests.support.core_api import measure_value, verify_value

_REPO = Path(__file__).resolve().parents[3]
_CONFIG = _REPO / "tests" / "fixtures" / "core.toml"


def main() -> None:
    col.config.load_config(str(_CONFIG))
    measure_value(key="rx_level", value=0.0)
    verify_value(key="rx_level", expected_val=0.0, tolerance=0.5)


if __name__ == "__main__":
    main()
    col.endex()
