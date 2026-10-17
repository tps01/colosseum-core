"""Passing test that calls col.endex() (suite slot finalize, no process exit)."""

from __future__ import annotations

import colosseum as col


def main() -> None:
    col.endex()
