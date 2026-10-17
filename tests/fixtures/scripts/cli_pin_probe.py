"""Script that tries to override CLI -g / -m (should be ignored when pinned)."""

from __future__ import annotations

from pathlib import Path

import colosseum as col

_FIXTURES = Path(__file__).resolve().parents[1]
_SCRIPT_CONFIG = _FIXTURES / "script_override.toml"
_SCRIPT_META = _FIXTURES / "script_override_metadata.yaml"


def main() -> None:
    col.config.load_config(str(_SCRIPT_CONFIG))
    col.config.load_metadata(str(_SCRIPT_META))
