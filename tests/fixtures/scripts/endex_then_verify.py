"""Call endex() then a verification — must not allocate a sibling outputs dir."""

from __future__ import annotations

import colosseum as col
from colosseum.decorators import verification


@verification()
def after_endex_check(*, key: str) -> bool:
    _ = key
    return True


def main() -> None:
    col.endex()
    after_endex_check(key="after")
