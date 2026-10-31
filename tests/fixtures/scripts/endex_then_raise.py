"""Call endex() then raise — suite must fail after the slot folder is closed."""

from __future__ import annotations

import colosseum as col


def main() -> None:
    col.endex()
    raise RuntimeError("induced after endex")
