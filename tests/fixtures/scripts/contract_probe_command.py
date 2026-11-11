"""Call the contract_probe plugin @command from a script run by ``colosseum run``."""

from __future__ import annotations

import colosseum as col


def main() -> None:
    if col.contract_probe.ping() != "pong":
        raise SystemExit("ping() did not return pong")
