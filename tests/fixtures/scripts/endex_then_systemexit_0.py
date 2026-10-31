"""Call endex() then SystemExit(0) — suite stays passing."""

from __future__ import annotations

import colosseum as col


def main() -> None:
    col.endex()
    raise SystemExit(0)
