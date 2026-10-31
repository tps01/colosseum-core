"""Call endex() then SystemExit(1) — suite must fail."""

from __future__ import annotations

import colosseum as col


def main() -> None:
    col.endex()
    raise SystemExit(1)
