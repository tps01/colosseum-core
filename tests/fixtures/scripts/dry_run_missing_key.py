"""Measurement without a key so a dry-run suite slot fails and the walk continues."""

from __future__ import annotations

from pathlib import Path

import colosseum as col

from tests.support.core_api import measure_value

_REPO = Path(__file__).resolve().parents[3]
_CONFIG = _REPO / "tests" / "fixtures" / "core.toml"


def main() -> None:
    col.config.load_config(str(_CONFIG))
    measure_value(value=1.0)
    measure_value(key="later", value=2.0)


if __name__ == "__main__":
    main()
    col.endex()
