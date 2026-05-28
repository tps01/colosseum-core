"""Test script that raises without recording verifications (suite semantics fixture)."""


def main() -> None:
    raise RuntimeError("intentional test script failure")
