"""Teardown script that raises KeyboardInterrupt (signal-like propagation)."""


def main() -> None:
    raise KeyboardInterrupt("induced in teardown")
